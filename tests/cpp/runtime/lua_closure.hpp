#pragma once

/**
 * lua_closure.hpp — High-performance Lua closure + upvalue implementation
 *
 * Design goals:
 *  - Match LuaJIT's closure memory layout exactly where it matters
 *  - Open upvalues are stack-resident (zero allocation on the hot path)
 *  - Closing upvalues heap-allocates exactly once, all closures sharing
 *    the same upvalue see the write immediately (shared mutable cell)
 *  - Proto (function prototype) is immutable after compilation and shared
 *    across all closures created from the same source function
 *  - C closures and Lua closures share a common GCObject header so the
 *    interpreter dispatch is a single tag check
 *  - Upvalue array is flexible-array-member allocated inline with the
 *    Closure struct (one allocation, good locality)
 *
 * Key concepts:
 *
 *   Proto      — compiled bytecode + constants + debug info (immutable)
 *   UpVal      — mutable cell; points INTO the stack while open,
 *                becomes self-contained when closed
 *   LuaClosure — Proto* + N UpVal* pointers (flexible array member)
 *   CClosure   — C function pointer + N captured TValues (flexible array)
 *
 * Open/close lifecycle:
 *
 *   1. Function is called → interpreter creates LuaClosure on heap,
 *      UpVal* array filled with pointers to open UpVal nodes that
 *      point directly into the calling frame's stack slots.
 *
 *   2. While the enclosing function is still running, all UpVal nodes
 *      for the same stack slot are linked in a singly-linked list
 *      (openList) anchored in the CallState / coroutine thread.
 *      Reading/writing the upvalue = dereferencing one pointer (hot).
 *
 *   3. When the enclosing frame returns (lua_close_upvalues), every
 *      UpVal whose stack slot is about to be invalidated copies the
 *      TValue into UpVal::closed and flips val ptr → &closed.
 *      Cost: one copy + one pointer write per closed-over variable.
 *
 *   4. After closing, all closures sharing that UpVal* still work
 *      correctly — they read/write UpVal::closed through the same ptr.
 */

#include "lua_table.hpp"   // brings in TValue, LIKELY, UNLIKELY, etc.
#include <cstdint>
#include <cstring>
#include <cassert>
#include <atomic>

// ============================================================
// Forward declarations
// ============================================================
struct Proto;
struct UpVal;
struct LuaClosure;
struct CClosure;
struct CallState;   // interpreter call frame / coroutine state

// ============================================================
// GC object kinds (fits in one byte)
// ============================================================
enum class GCKind : uint8_t {
    String    = 0,
    Table     = 1,
    Proto     = 2,
    UpVal     = 3,
    LuaClosure = 4,
    CClosure  = 5,
    Thread    = 6,
    Userdata  = 7,
};

// ============================================================
// GCHeader — common prefix for all heap-allocated GC objects
// 8 bytes, fits in the same cache line as the object's hot fields
// ============================================================
struct GCHeader {
    GCObject*  next;       // intrusive GC list
    GCKind     kind;
    uint8_t    marked;     // GC mark bits (tri-color)
    uint16_t   reserved;
    uint32_t   refcount;   // optional refcount for deterministic destroy
};

static_assert(sizeof(GCHeader) == 16, "GCHeader should be 16 bytes");

// ============================================================
// UpValState — distinguishes open vs closed
// ============================================================
enum class UpValState : uint8_t {
    Open   = 0,  // val points into a live stack frame
    Closed = 1,  // val points to self->closed
};

// ============================================================
// UpVal — the mutable shared cell
//
// Memory layout (32 bytes, fits in half a cache line):
//
//  [GCHeader  16B]
//  [TValue*    8B]  val  → stack slot (open) or &closed (closed)
//  [UpVal*     8B]  openNext → next open upvalue in thread's list
//   ... (closed TValue stored via flexible tail, see below) ...
//
// We embed the closed value RIGHT AFTER the fixed fields so that
// the "closed" path writes to a slot in the same allocation.
// ============================================================
struct UpVal {
    GCHeader   gc;
    TValue*    val;        // hot: dereference this to get/set the value
    UpValState state;
    uint8_t    _pad[7];

    // Linked list of open upvalues per thread (keyed by stack level)
    UpVal*     openNext;   // next upvalue at a higher stack level
    TValue*    stackSlot;  // which stack slot we point to (for close detection)

    // When closed, the value lives here:
    TValue     closed;

    // ---- Factory --------------------------------------------------
    // Create an open upvalue pointing to a stack slot.
    // Caller is responsible for inserting into the thread's openList.
    static UpVal* create(TValue* stackSlot) {
        UpVal* uv = new UpVal();
        uv->gc.kind   = GCKind::UpVal;
        uv->gc.marked = 0;
        uv->gc.refcount = 1;
        uv->state     = UpValState::Open;
        uv->val       = stackSlot;
        uv->stackSlot = stackSlot;
        uv->openNext  = nullptr;
        uv->closed    = TValue::Nil();
        return uv;
    }

    // ---- Close ----------------------------------------------------
    // Called when the stack frame owning our slot is about to die.
    // Copies the current value into self->closed and redirects val.
    ALWAYS_INLINE void close() {
        assert(state == UpValState::Open);
        closed = *val;          // copy stack slot value into self
        val    = &closed;       // redirect pointer
        state  = UpValState::Closed;
        stackSlot = nullptr;
    }

    // ---- Value access (always through val pointer) ----------------
    ALWAYS_INLINE TValue  get()              const { return *val; }
    ALWAYS_INLINE void    set(TValue v)            { *val = v; }
    ALWAYS_INLINE TValue& ref()                    { return *val; }

    // Is this upvalue on the stack at or above 'level'?
    ALWAYS_INLINE bool isAbove(TValue* level) const {
        return state == UpValState::Open && stackSlot >= level;
    }
};

static_assert(sizeof(UpVal) <= 64, "UpVal should fit in one cache line");

// ============================================================
// Proto — immutable function prototype (shared across closures)
//
// Produced by the compiler; never modified after creation.
// All closures from the same source function share ONE Proto*.
//
// Layout chosen for sequential access during interpretation:
//   code[] first (fetched every instruction)
//   k[]    second (constants, fetched for LOAD_K opcodes)
//   upvalueDescs[] third (only touched at closure creation time)
// ============================================================

// Upvalue descriptor: tells the closure factory where to find
// each upvalue when a new closure is instantiated.
struct UpValDesc {
    uint8_t  instack;  // 1 = captured from enclosing function's locals (stack)
                       // 0 = captured from enclosing function's upvalue list
    uint8_t  idx;      // stack slot index (instack=1) or upvalue index (instack=0)
    uint8_t  kind;     // UpValKind hint for optimizer (regular, immutable, etc.)
    uint8_t  _pad;
    // Debug info
    const char* name;  // upvalue name (interned string or nullptr)
};

// Instruction type — 32-bit fixed-width (LuaJIT/PUC compatible)
using Instruction = uint32_t;

// Opcode field extraction (adjust to your VM's encoding)
inline uint8_t  OP(Instruction i)  { return i & 0xff; }
inline uint8_t  A(Instruction i)   { return (i >> 8) & 0xff; }
inline uint16_t Bx(Instruction i)  { return (i >> 16) & 0xffff; }
inline int16_t  sBx(Instruction i) { return (int16_t)((i >> 16) & 0xffff) - 32767; }

struct Proto {
    GCHeader gc;

    // ---- Hot fields (accessed every instruction) ----
    const Instruction* code;    // bytecode array
    uint32_t           codeSize;

    // ---- Warm fields (accessed for LOAD_K, calls) ----
    const TValue*      k;       // constant pool
    uint32_t           kSize;

    // ---- Cold fields (accessed once at closure creation) ----
    const UpValDesc*   upvalueDescs;
    uint8_t            numUpvalues;  // number of upvalues this proto closes over
    uint8_t            numParams;    // number of fixed parameters
    uint8_t            isVararg;     // does the function accept '...'?
    uint8_t            maxStack;     // max stack slots needed

    // Sub-functions (inner Proto*s for nested function literals)
    Proto**  protos;
    uint32_t numProtos;

    // Debug info (nullable — stripped in release builds)
    const char*    source;       // source file name
    const int*     lineInfo;     // instruction → source line mapping
    const char**   localNames;   // local variable names
    uint32_t       numLocals;
    int            lineDefined;
    int            lastLineDefined;

    // Refcount for lifetime management (Protos are long-lived)
    void ref()   { gc.refcount++; }
    void unref() { if (--gc.refcount == 0) destroy(); }

    static Proto* create(uint32_t codeSize, uint32_t kSize,
                         uint8_t numUpvalues, uint8_t maxStack) {
        Proto* p = new Proto();
        p->gc.kind     = GCKind::Proto;
        p->gc.marked   = 0;
        p->gc.refcount = 1;
        p->codeSize    = codeSize;
        p->kSize       = kSize;
        p->numUpvalues = numUpvalues;
        p->maxStack    = maxStack;
        p->numParams   = 0;
        p->isVararg    = 0;
        p->numProtos   = 0;
        p->protos      = nullptr;
        p->source      = nullptr;
        p->lineInfo    = nullptr;
        p->localNames  = nullptr;
        p->numLocals   = 0;
        p->lineDefined = 0;
        p->lastLineDefined = 0;

        // Allocate mutable arrays (compiler fills these in)
        p->code         = new Instruction[codeSize]();
        p->k            = new TValue[kSize]();
        p->upvalueDescs = new UpValDesc[numUpvalues]();
        return p;
    }

private:
    void destroy() {
        delete[] code;
        delete[] k;
        delete[] upvalueDescs;
        if (protos) {
            for (uint32_t i = 0; i < numProtos; i++)
                if (protos[i]) protos[i]->unref();
            delete[] protos;
        }
        delete this;
    }
};

// ============================================================
// LuaClosure — a Proto + captured upvalue pointers
//
// The upvalue pointer array is allocated INLINE with the struct
// via flexible array member → single allocation, excellent locality.
//
//   sizeof(LuaClosure) + n * sizeof(UpVal*)
//
// This mirrors LuaJIT's GCfuncL layout exactly.
// ============================================================
struct LuaClosure {
    GCHeader gc;
    Proto*   proto;         // shared, immutable
    LuaTable* env;          // _ENV upvalue table (Lua 5.2+)
    uint8_t  numUpvalues;
    uint8_t  _pad[7];
    UpVal*   upvals[1];     // flexible: upvals[0..numUpvalues-1]
                             // (C99 FAM style — last member, size 1 for C++)

    // ---- Factory ------------------------------------------------
    // Allocate a LuaClosure for `proto` with `n` upvalue slots.
    // Caller must fill upvals[] immediately after creation.
    static LuaClosure* create(Proto* proto) {
        uint8_t n = proto->numUpvalues;
        // Single allocation: header + (n-1) extra UpVal* slots
        size_t sz = sizeof(LuaClosure) + (n > 1 ? (n - 1) * sizeof(UpVal*) : 0);
        void* mem = ::operator new(sz);
        LuaClosure* cl = new(mem) LuaClosure();
        cl->gc.kind     = GCKind::LuaClosure;
        cl->gc.marked   = 0;
        cl->gc.refcount = 1;
        cl->proto       = proto;
        cl->env         = nullptr;
        cl->numUpvalues = n;
        proto->ref();
        // Zero-initialize upvalue slots
        std::memset(cl->upvals, 0, n * sizeof(UpVal*));
        return cl;
    }

    void destroy() {
        for (uint8_t i = 0; i < numUpvalues; i++)
            if (upvals[i]) releaseUpVal(upvals[i]);
        proto->unref();
        this->~LuaClosure();
        ::operator delete(this);
    }

    // ---- Upvalue access (hot path — one pointer deref) ----------
    ALWAYS_INLINE TValue  getUpval(uint8_t i) const {
        assert(i < numUpvalues);
        return upvals[i]->get();
    }
    ALWAYS_INLINE void setUpval(uint8_t i, TValue v) {
        assert(i < numUpvalues);
        upvals[i]->set(v);
    }
    ALWAYS_INLINE UpVal* upval(uint8_t i) const {
        assert(i < numUpvalues);
        return upvals[i];
    }

private:
    static void releaseUpVal(UpVal* uv) {
        if (--uv->gc.refcount == 0) delete uv;
    }
};

// ============================================================
// CClosure — a C function + captured TValues
//
// C closures store their captured values INLINE (not as UpVal*)
// because C functions manage their own state — there's no VM
// stack to point into, so the "open upvalue" optimization doesn't
// apply. Values are copied in by value at capture time.
//
// Layout: GCHeader + fn ptr + n TValues
// ============================================================
using LuaCFunction = int(*)(void* L);  // int lua_CFunction(lua_State*)

struct CClosure {
    GCHeader     gc;
    LuaCFunction fn;
    uint8_t      numUpvalues;
    uint8_t      _pad[7];
    TValue       upvals[1];  // flexible: upvals[0..numUpvalues-1]

    static CClosure* create(LuaCFunction fn, uint8_t n) {
        size_t sz = sizeof(CClosure) + (n > 1 ? (n - 1) * sizeof(TValue) : 0);
        void* mem = ::operator new(sz);
        CClosure* cl = new(mem) CClosure();
        cl->gc.kind     = GCKind::CClosure;
        cl->gc.marked   = 0;
        cl->gc.refcount = 1;
        cl->fn          = fn;
        cl->numUpvalues = n;
        for (uint8_t i = 0; i < n; i++) cl->upvals[i] = TValue::Nil();
        return cl;
    }

    void destroy() {
        this->~CClosure();
        ::operator delete(this);
    }

    ALWAYS_INLINE TValue  getUpval(uint8_t i) const { assert(i<numUpvalues); return upvals[i]; }
    ALWAYS_INLINE void    setUpval(uint8_t i, TValue v) { assert(i<numUpvalues); upvals[i] = v; }
    ALWAYS_INLINE TValue& upvalRef(uint8_t i)       { assert(i<numUpvalues); return upvals[i]; }

    // Call the C function
    ALWAYS_INLINE int call(void* L) { return fn(L); }
};

// ============================================================
// Closure — type-erased union view (like LuaJIT's GCfunc)
//
// The interpreter casts GCObject* to Closure* and checks the
// GCKind tag to decide which variant it is. No vtable needed.
// ============================================================
struct Closure {
    GCHeader gc; // same offset in both LuaClosure and CClosure

    bool isLua() const { return gc.kind == GCKind::LuaClosure; }
    bool isC()   const { return gc.kind == GCKind::CClosure;   }

    LuaClosure* asLua() {
        assert(isLua());
        return reinterpret_cast<LuaClosure*>(this);
    }
    CClosure* asC() {
        assert(isC());
        return reinterpret_cast<CClosure*>(this);
    }
};

// ============================================================
// UpVal open list management — per call-state/thread
//
// The interpreter keeps a singly-linked list of all open upvalues
// sorted descending by stack level (highest stack slot first).
// This makes `closeUpvalues(level)` a simple front-of-list scan.
// ============================================================

// Find or create an open upvalue for a given stack slot.
// `openList` is the thread's head pointer (UpVal**).
// O(n) in the number of currently-open upvalues — in practice
// functions close over very few variables so this is fine.
ALWAYS_INLINE UpVal* findOrCreateUpVal(UpVal** openList, TValue* slot) {
    // Walk the list looking for an existing upvalue at this slot
    UpVal** pp = openList;
    while (*pp) {
        UpVal* uv = *pp;
        // Open upvalues are sorted by stack level (descending).
        // If we've gone past where this slot would be, it doesn't exist.
        if (uv->stackSlot < slot) break;
        if (uv->stackSlot == slot) return uv; // found it — share!
        pp = &uv->openNext;
    }
    // Not found: create a new open upvalue and insert into sorted position
    UpVal* uv  = UpVal::create(slot);
    uv->openNext = *pp;
    *pp = uv;
    return uv;
}

// Close all upvalues at or above `level` in the stack.
// Called when a block exits or a function returns.
// This is the ONLY place where Open → Closed transition happens.
ALWAYS_INLINE void closeUpvalues(UpVal** openList, TValue* level) {
    while (*openList && (*openList)->stackSlot >= level) {
        UpVal* uv = *openList;
        *openList = uv->openNext;
        uv->close();
        uv->openNext = nullptr;
    }
}

// ============================================================
// Closure instantiation — the "new closure" interpreter opcode
//
// Called when the VM executes OP_CLOSURE.
// `enclosing` is the closure of the currently executing function.
// `stack` is a pointer to the current frame's base stack slot.
// `openList` is &thread->openUpvals.
// ============================================================
NOINLINE LuaClosure* instantiateClosure(
        Proto*      proto,
        LuaClosure* enclosing,
        TValue*     stack,
        UpVal**     openList)
{
    LuaClosure* cl = LuaClosure::create(proto);

    for (uint8_t i = 0; i < proto->numUpvalues; i++) {
        const UpValDesc& desc = proto->upvalueDescs[i];
        if (desc.instack) {
            // Capture a local variable from the enclosing stack frame.
            // Finds or creates the shared open UpVal node.
            cl->upvals[i] = findOrCreateUpVal(openList, stack + desc.idx);
            cl->upvals[i]->gc.refcount++;  // closure holds a reference
        } else {
            // Capture an upvalue that the enclosing function itself closes over.
            assert(enclosing && desc.idx < enclosing->numUpvalues);
            UpVal* uv = enclosing->upvals[desc.idx];
            cl->upvals[i] = uv;
            uv->gc.refcount++;
        }
    }
    return cl;
}

// ============================================================
// TValue factory helpers for closure types
// (Extends TValue with Closure/CClosure constructors)
// ============================================================
namespace TValueExt {
    inline TValue FromLuaClosure(LuaClosure* cl) {
        return TValue(TValue::TAG_FUNCTION |
                      (reinterpret_cast<uint64_t>(cl) & TValue::POINTER_MASK));
    }
    inline TValue FromCClosure(CClosure* cl) {
        return TValue(TValue::TAG_FUNCTION |
                      (reinterpret_cast<uint64_t>(cl) & TValue::POINTER_MASK));
    }
    inline Closure* ToClosure(TValue v) {
        assert((v.bits & TValue::TAG_MASK) == TValue::TAG_FUNCTION);
        return reinterpret_cast<Closure*>(v.bits & TValue::POINTER_MASK);
    }
}

// ============================================================
// Example: minimal call frame to show everything wired together
// ============================================================
struct CallFrame {
    LuaClosure*  closure;    // currently executing closure
    Instruction* pc;         // program counter into closure->proto->code
    TValue*      base;       // base of this frame's stack window
    int          nResults;   // expected result count (-1 = vararg)
};

/**
 * Demonstration of how a minimal interpreter loop would use this:
 *
 *   void execute(CallFrame* frame, TValue* stack, UpVal** openList) {
 *       Proto*       p  = frame->closure->proto;
 *       Instruction* pc = frame->pc;
 *
 *       for (;;) {
 *           Instruction ins = *pc++;
 *           switch (OP(ins)) {
 *
 *           case OP_GETUPVAL: {
 *               // GETUPVAL A, B  →  R(A) = UpValue[B]
 *               uint8_t a = A(ins), b = (uint8_t)Bx(ins);
 *               frame->base[a] = frame->closure->getUpval(b);
 *               break;
 *           }
 *           case OP_SETUPVAL: {
 *               // SETUPVAL A, B  →  UpValue[B] = R(A)
 *               uint8_t a = A(ins), b = (uint8_t)Bx(ins);
 *               frame->closure->setUpval(b, frame->base[a]);
 *               break;
 *           }
 *           case OP_CLOSURE: {
 *               // CLOSURE A, Bx  →  R(A) = closure(Proto[Bx])
 *               uint8_t  a  = A(ins);
 *               uint16_t bx = Bx(ins);
 *               Proto*   np = p->protos[bx];
 *               LuaClosure* cl = instantiateClosure(
 *                   np, frame->closure, frame->base, openList);
 *               frame->base[a] = TValueExt::FromLuaClosure(cl);
 *               break;
 *           }
 *           case OP_RETURN: {
 *               // Close any upvalues living in this frame
 *               closeUpvalues(openList, frame->base);
 *               return;
 *           }
 *           // ... other opcodes ...
 *           }
 *       }
 *   }
 */