#pragma once

/**
 * lua_table.hpp - High-performance Lua table implementation
 *
 * Design:
 *  - NaN-boxed TValue (8 bytes, from your implementation)
 *  - Hybrid array part (dense integer keys 1..n) + hash part
 *  - Swiss Table (SIMD flat open-addressing) for hash part
 *  - Robin Hood insertion for low probe variance
 *  - wyhash for string/pointer keys
 *  - Cache-line aligned Table header
 *  - Branchless fast paths for integer-in-array case
 */

#include <cstdint>
#include <cstring>
#include <cassert>
#include <cmath>
#include <new>
#include <algorithm>
#include <string>
#include <functional>
#include <optional>

// ============================================================
// Platform / SIMD helpers
// ============================================================
#if defined(__SSE2__)
#  include <immintrin.h>
#  define LUATABLE_SIMD 1
#endif

#if defined(__GNUC__) || defined(__clang__)
#  define LIKELY(x)   __builtin_expect(!!(x), 1)
#  define UNLIKELY(x) __builtin_expect(!!(x), 0)
#  define ALWAYS_INLINE __attribute__((always_inline)) inline
#  define NOINLINE      __attribute__((noinline))
#else
#  define LIKELY(x)   (x)
#  define UNLIKELY(x) (x)
#  define ALWAYS_INLINE inline
#  define NOINLINE
#endif

// ============================================================
// Forward declarations
// ============================================================
struct GCObject;
struct LuaTable;
struct Closure;
struct Userdata;
struct Thread;
struct TableSlotProxy;  // Forward declaration for operator[] return type

// ============================================================
// TValue — NaN-boxed tagged value (8 bytes)
// Identical to your implementation, reproduced here for
// self-containment and minor perf tweaks.
// ============================================================
class TValue {
public:
    uint64_t bits;  // public so Table nodes can be trivially copied

    static constexpr uint64_t NANBOX_BASE = 0xfff8000000000000ULL;
    static constexpr uint64_t TAG_NIL       = 0xfff8000000000000ULL;
    static constexpr uint64_t TAG_FALSE     = 0xfff9000000000000ULL;
    static constexpr uint64_t TAG_TRUE      = 0xfffa000000000000ULL;
    static constexpr uint64_t TAG_LIGHTUD   = 0xfffb000000000000ULL;
    static constexpr uint64_t TAG_STRING    = 0xfffc000000000000ULL;
    static constexpr uint64_t TAG_UPVAL     = 0xfffd000000000000ULL;
    static constexpr uint64_t TAG_THREAD    = 0xfffe000000000000ULL;
    static constexpr uint64_t TAG_PROTO     = 0xffff000000000000ULL;
    static constexpr uint64_t TAG_FUNCTION  = 0xfff8800000000000ULL;
    static constexpr uint64_t TAG_TABLE     = 0xfff9800000000000ULL;
    static constexpr uint64_t TAG_USERDATA  = 0xfffa800000000000ULL;
    static constexpr uint64_t TAG_INT       = 0xfffb800000000000ULL;
    static constexpr uint64_t POINTER_MASK  = 0x00007fffffffffffULL;
    static constexpr uint64_t TAG_MASK      = 0xffff800000000000ULL;

    // Function type for callable TValue support
    using FuncType = std::function<TValue(TValue, TValue)>;

    TValue() : bits(TAG_NIL) {}
    explicit TValue(uint64_t raw) : bits(raw) {}
    TValue(double d) { std::memcpy(&bits, &d, 8); }
    TValue(int32_t i) : bits(TAG_INT | (uint32_t)i) {}
    TValue(const char* s) { *this = String(s); }  // For compatibility with TABLE(argv[i])

    static TValue Nil()               { return TValue(TAG_NIL); }
    static TValue Boolean(bool b)     { return TValue(b ? TAG_TRUE : TAG_FALSE); }
    static TValue Integer(int32_t i)  { return TValue(TAG_INT | (uint32_t)i); }
    static TValue Number(double d)    { TValue v; std::memcpy(&v.bits, &d, 8); return v; }

    static TValue String(const void* p) {
        return TValue(TAG_STRING | (reinterpret_cast<uint64_t>(p) & POINTER_MASK));
    }
    static TValue Table(LuaTable* p) {
        return TValue(TAG_TABLE | (reinterpret_cast<uint64_t>(p) & POINTER_MASK));
    }
    static TValue LightUD(void* p) {
        return TValue(TAG_LIGHTUD | (reinterpret_cast<uint64_t>(p) & POINTER_MASK));
    }
    static TValue Function(FuncType* p) {
        return TValue(TAG_FUNCTION | (reinterpret_cast<uint64_t>(p) & POINTER_MASK));
    }

    ALWAYS_INLINE bool isNil()     const { return bits == TAG_NIL; }
    ALWAYS_INLINE bool isInteger() const { return (bits & TAG_MASK) == TAG_INT; }
    ALWAYS_INLINE bool isNumber()  const { return (bits & NANBOX_BASE) != NANBOX_BASE; }
    ALWAYS_INLINE bool isString()  const { return (bits & TAG_MASK) == TAG_STRING; }
    ALWAYS_INLINE bool isTable()   const { return (bits & TAG_MASK) == TAG_TABLE; }
    ALWAYS_INLINE bool isFunction() const { return (bits & TAG_MASK) == TAG_FUNCTION; }
    ALWAYS_INLINE bool isFalsy()   const { return bits == TAG_NIL || bits == TAG_FALSE; }

    ALWAYS_INLINE int32_t    toInteger() const { return (int32_t)(bits & 0xffffffff); }
    ALWAYS_INLINE double     toNumber()  const { double d; std::memcpy(&d, &bits, 8); return d; }
    ALWAYS_INLINE const void* toPtr()   const { return reinterpret_cast<const void*>(bits & POINTER_MASK); }
    ALWAYS_INLINE LuaTable*  toTable()  const { return reinterpret_cast<LuaTable*>(bits & POINTER_MASK); }
    ALWAYS_INLINE FuncType* toFunction() const { 
        return reinterpret_cast<FuncType*>(bits & POINTER_MASK); 
    }

    TValue call(TValue a, TValue b) const {
        if (isFunction()) {
            FuncType* f = toFunction();
            if (f && *f) return (*f)(a, b);
        }
        return Nil();
    }
    
    // Numeric value extraction (for arithmetic)
    ALWAYS_INLINE double asNumber() const {
        if (isNumber()) return toNumber();
        if (isInteger()) return (double)toInteger();
        if (isString()) {
            // Convert string to number (Lua semantics)
            const char* s = static_cast<const char*>(toPtr());
            char* end;
            double d = std::strtod(s, &end);
            if (end != s && *end == '\0') {
                return d;
            }
        }
        return 0.0;
    }
    
    // Implicit conversion to double (for transpiler compatibility)
    operator double() const { return asNumber(); }

    // Total equality (same bits = same value, consistent with Lua rawequal)
    ALWAYS_INLINE bool operator==(TValue o) const {
        // Fast path: same bits = same value
        if (bits == o.bits) return true;
        // String content comparison
        if (isString() && o.isString()) {
            const char* a = static_cast<const char*>(toPtr());
            const char* b = static_cast<const char*>(o.toPtr());
            return std::strcmp(a, b) == 0;
        }
        return false;
    }
    ALWAYS_INLINE bool operator!=(TValue o) const { return bits != o.bits; }
    
    // Comparison with double (resolves ambiguity with implicit conversion)
    ALWAYS_INLINE bool operator>=(double o) const { return asNumber() >= o; }
    ALWAYS_INLINE bool operator==(double d) const { return asNumber() == d; }
    ALWAYS_INLINE bool operator!=(double d) const { return asNumber() != d; }
    
    // Comparison with int (resolves ambiguity with implicit conversion)
    ALWAYS_INLINE bool operator==(int i) const { return isInteger() ? toInteger() == i : asNumber() == i; }
    ALWAYS_INLINE bool operator!=(int i) const { return isInteger() ? toInteger() != i : asNumber() != i; }
    
    // Truthiness (same semantics as isFalsy but inverted, for bool conversion)
    explicit operator bool() const { return !isFalsy(); }
    bool operator!() const { return isFalsy(); }
    
    // Assignment from double (for transpiler compatibility)
    TValue& operator=(double d) { *this = Number(d); return *this; }

    // Assignment from TableSlotProxy to fix ambiguous overloads
    TValue& operator=(const TableSlotProxy& other);

    // Accept callable types (function pointers, lambdas) and wrap as TValue::Function
    template<typename F, typename = std::enable_if_t<
        std::is_invocable_v<F> && 
        !std::is_same_v<std::decay_t<F>, TValue> &&
        !std::is_convertible_v<F, double>
    >>
    TValue& operator=(F&& f) {
        *this = Function(new FuncType(std::forward<F>(f)));
        return *this;
    }

    // Comparison operators with TableSlotProxy (fixes heapsort ambiguity)
    bool operator<(const TableSlotProxy& o) const;
    bool operator>(const TableSlotProxy& o) const;
    bool operator<=(const TableSlotProxy& o) const;
    bool operator>=(const TableSlotProxy& o) const;
    
    // Arithmetic operators with metamethod dispatch (defined after get_metamethod)
    ALWAYS_INLINE TValue operator*(const TValue& o) const;
    ALWAYS_INLINE TValue operator+(const TValue& o) const;
    ALWAYS_INLINE TValue operator-(const TValue& o) const;
    ALWAYS_INLINE TValue operator/(const TValue& o) const;
    
    // Table access operators (defined after LuaTable)
    TableSlotProxy operator[](int32_t index);
    TValue         operator[](int32_t index) const;
    TableSlotProxy operator[](double index);
    TValue         operator[](double index) const;
    TableSlotProxy operator[](const char* key);
    TValue         operator[](const char* key) const;
    TableSlotProxy operator[](const std::string& key);
    TValue         operator[](const std::string& key) const;
    TableSlotProxy operator[](const TableSlotProxy& key);  // For table[proxy]
    TValue         operator[](const TableSlotProxy& key) const;
};

static_assert(sizeof(TValue) == 8, "TValue must be 8 bytes");

// ============================================================
// wyhash — fast, high-quality 64-bit hash
// Public domain, see https://github.com/wangyi-fudan/wyhash
// ============================================================
namespace wyhash_impl {
    ALWAYS_INLINE uint64_t wymix(uint64_t a, uint64_t b) {
        __uint128_t r = (__uint128_t)a * b;
        return (uint64_t)(r) ^ (uint64_t)(r >> 64);
    }
    ALWAYS_INLINE uint64_t wyr8(const uint8_t* p) {
        uint64_t v; std::memcpy(&v, p, 8); return v;
    }
    ALWAYS_INLINE uint64_t wyr4(const uint8_t* p) {
        uint32_t v; std::memcpy(&v, p, 4); return v;
    }

    inline uint64_t wyhash(const void* key, size_t len, uint64_t seed = 0) {
        static constexpr uint64_t P0 = 0xa0761d6478bd642full;
        static constexpr uint64_t P1 = 0xe7037ed1a0b428dbull;
        static constexpr uint64_t P2 = 0x8ebc6af09c88c6e3ull;
        static constexpr uint64_t P3 = 0x589965cc75374cc3ull;

        const uint8_t* p = (const uint8_t*)key;
        seed ^= P0;
        uint64_t a = 0, b = 0;
        if (LIKELY(len <= 16)) {
            if (LIKELY(len >= 4)) {
                a = (wyr4(p) << 32) | wyr4(p + ((len >> 3) << 2));
                b = (wyr4(p + len - 4) << 32) | wyr4(p + len - 4 - ((len >> 3) << 2));
            } else if (len > 0) {
                a = ((uint64_t)p[0] << 16) | ((uint64_t)p[len >> 1] << 8) | p[len - 1];
            }
        } else {
            size_t i = len;
            if (UNLIKELY(i > 48)) {
                uint64_t s1 = seed, s2 = seed;
                do {
                    seed = wymix(wyr8(p)^P1, wyr8(p+8)^seed);
                    s1   = wymix(wyr8(p+16)^P2, wyr8(p+24)^s1);
                    s2   = wymix(wyr8(p+32)^P3, wyr8(p+40)^s2);
                    p += 48; i -= 48;
                } while (LIKELY(i > 48));
                seed ^= s1 ^ s2;
            }
            while (UNLIKELY(i > 16)) {
                seed = wymix(wyr8(p)^P1, wyr8(p+8)^seed);
                p += 16; i -= 16;
            }
            a = wyr8(p + i - 16);
            b = wyr8(p + i - 8);
        }
        return wymix(P1^len, wymix(a^P1, b^seed));
    }
} // namespace wyhash_impl

// Hash string content (for non-interned strings)
ALWAYS_INLINE uint32_t hashString(const char* s, size_t len) {
    return (uint32_t)wyhash_impl::wyhash(s, len);
}

// ============================================================
// Key hashing for TValue keys
// ============================================================
ALWAYS_INLINE uint32_t hashTValue(TValue key) {
    if (key.isInteger()) {
        // Finalizer mix for integers (Thomas Wang)
        uint32_t k = (uint32_t)key.toInteger();
        k = ((k >> 16) ^ k) * 0x45d9f3b;
        k = ((k >> 16) ^ k) * 0x45d9f3b;
        k = (k >> 16) ^ k;
        return k;
    }
    if (key.isString()) {
        // Hash string content (not pointer) for correct metamethod lookup
        const char* s = static_cast<const char*>(key.toPtr());
        return hashString(s, std::strlen(s));
    }
    // For all other types (doubles, pointers): hash the raw bits
    return (uint32_t)wyhash_impl::wymix(key.bits, 0x9e3779b97f4a7c15ULL);
}

// ============================================================
// Swiss Table control byte constants
// ============================================================
static constexpr int8_t CTRL_EMPTY   = -128;  // 0x80
static constexpr int8_t CTRL_DELETED = -2;    // 0xFE
// h2 (lower 7 bits of hash) stored as non-negative value [0, 127]

// ============================================================
// HashGroup — 16-slot SIMD group (one cache line of ctrl bytes)
// ============================================================
struct alignas(16) HashGroup {
    int8_t ctrl[16];

    void init() { std::memset(ctrl, CTRL_EMPTY, 16); }

#ifdef LUATABLE_SIMD
    // Returns bitmask of slots matching h2
    ALWAYS_INLINE uint32_t matchH2(int8_t h2) const {
        __m128i c = _mm_load_si128((__m128i*)ctrl);
        __m128i t = _mm_set1_epi8(h2);
        return (uint32_t)_mm_movemask_epi8(_mm_cmpeq_epi8(c, t));
    }
    // Returns bitmask of empty slots
    ALWAYS_INLINE uint32_t matchEmpty() const {
        __m128i c = _mm_load_si128((__m128i*)ctrl);
        __m128i e = _mm_set1_epi8(CTRL_EMPTY);
        return (uint32_t)_mm_movemask_epi8(_mm_cmpeq_epi8(c, e));
    }
    // Returns bitmask of empty-or-deleted slots
    ALWAYS_INLINE uint32_t matchAvailable() const {
        __m128i c  = _mm_load_si128((__m128i*)ctrl);
        // Both EMPTY(0x80) and DELETED(0xFE) have high bit set
        return (uint32_t)_mm_movemask_epi8(c);
    }
#else
    ALWAYS_INLINE uint32_t matchH2(int8_t h2) const {
        uint32_t mask = 0;
        for (int i = 0; i < 16; i++)
            if (ctrl[i] == h2) mask |= (1u << i);
        return mask;
    }
    ALWAYS_INLINE uint32_t matchEmpty() const {
        uint32_t mask = 0;
        for (int i = 0; i < 16; i++)
            if (ctrl[i] == CTRL_EMPTY) mask |= (1u << i);
        return mask;
    }
    ALWAYS_INLINE uint32_t matchAvailable() const {
        uint32_t mask = 0;
        for (int i = 0; i < 16; i++)
            if ((uint8_t)ctrl[i] >= 0x80) mask |= (1u << i);
        return mask;
    }
#endif
};

// ============================================================
// HashSlot — key/value pair stored alongside ctrl bytes
// 16 bytes: one TValue key + one TValue value
// ============================================================
struct HashSlot {
    TValue key;
    TValue val;
};

// ============================================================
// HashPart — Swiss Table open-addressed hash
//
// Layout: groups of 16 ctrl bytes (one cache line), followed
// by the corresponding 16 HashSlots in a parallel array.
// capacity is always a multiple of 16 (power of 2 >=16).
// ============================================================
struct HashPart {
    HashGroup* groups;   // ctrl bytes, numGroups groups
    HashSlot*  slots;    // parallel slot array, numGroups*16 slots
    uint32_t   capacity; // total slots (numGroups * 16)
    uint32_t   count;    // live entries
    uint32_t   numGroups;

    // Derived: high bits of hash select group (h1), low 7 bits = h2
    ALWAYS_INLINE uint32_t h1(uint32_t hash) const {
        return (hash >> 7) % numGroups;
    }
    ALWAYS_INLINE int8_t h2(uint32_t hash) const {
        return (int8_t)(hash & 0x7f);
    }

    void init(uint32_t cap) {
        assert((cap & (cap - 1)) == 0 && cap >= 16);
        capacity  = cap;
        numGroups = cap / 16;
        count     = 0;
        // Allocate ctrl groups (cache-line aligned) + slots
        groups = (HashGroup*)::operator new(numGroups * sizeof(HashGroup) + 16,
                                            std::align_val_t{64});
        slots  = (HashSlot*)::operator new(cap * sizeof(HashSlot));
        for (uint32_t i = 0; i < numGroups; i++) groups[i].init();
    }

    void destroy() {
        ::operator delete(groups, std::align_val_t{64});
        ::operator delete(slots);
        groups = nullptr; slots = nullptr;
        capacity = count = numGroups = 0;
    }

    // Returns pointer to value for key, or nullptr if not found
    ALWAYS_INLINE TValue* find(TValue key) const {
        if (UNLIKELY(capacity == 0)) return nullptr;
        uint32_t hash = hashTValue(key);
        uint32_t g    = h1(hash);
        int8_t   h    = h2(hash);
        uint32_t gMask = numGroups - 1;

        for (;;) {
            uint32_t matches = groups[g].matchH2(h);
            while (matches) {
                uint32_t i = (uint32_t)__builtin_ctz(matches);
                uint32_t idx = g * 16 + i;
                if (LIKELY(slots[idx].key == key))
                    return &slots[idx].val;
                matches &= matches - 1;
            }
            if (LIKELY(groups[g].matchEmpty()))
                return nullptr; // probe sequence terminated
            g = (g + 1) & gMask;
        }
    }

    // Insert or update key. Returns pointer to value slot.
    // Caller must check load factor before calling.
    NOINLINE TValue* upsert(TValue key) {
        uint32_t hash  = hashTValue(key);
        uint32_t g     = h1(hash);
        int8_t   h     = h2(hash);
        uint32_t gMask = numGroups - 1;
        uint32_t firstAvailG = ~0u;
        uint32_t firstAvailI = ~0u;

        for (;;) {
            uint32_t matches = groups[g].matchH2(h);
            while (matches) {
                uint32_t i   = (uint32_t)__builtin_ctz(matches);
                uint32_t idx = g * 16 + i;
                if (LIKELY(slots[idx].key == key))
                    return &slots[idx].val; // update existing
                matches &= matches - 1;
            }
            // Track first available (empty or deleted) slot
            if (firstAvailG == ~0u) {
                uint32_t avail = groups[g].matchAvailable();
                if (avail) {
                    firstAvailG = g;
                    firstAvailI = (uint32_t)__builtin_ctz(avail);
                }
            }
            if (groups[g].matchEmpty()) break; // end of probe chain
            g = (g + 1) & gMask;
        }

        // Insert into first available slot
        assert(firstAvailG != ~0u);
        uint32_t idx = firstAvailG * 16 + firstAvailI;
        groups[firstAvailG].ctrl[firstAvailI] = h;
        slots[idx].key = key;
        slots[idx].val = TValue::Nil();
        count++;
        return &slots[idx].val;
    }

    // Remove key. Returns true if found.
    bool remove(TValue key) {
        if (UNLIKELY(capacity == 0)) return false;
        uint32_t hash  = hashTValue(key);
        uint32_t g     = h1(hash);
        int8_t   h     = h2(hash);
        uint32_t gMask = numGroups - 1;

        for (;;) {
            uint32_t matches = groups[g].matchH2(h);
            while (matches) {
                uint32_t i   = (uint32_t)__builtin_ctz(matches);
                uint32_t idx = g * 16 + i;
                if (slots[idx].key == key) {
                    // Use DELETED only if next group has entries
                    // (optimization: use EMPTY if no chain follows)
                    groups[g].ctrl[i] = CTRL_DELETED;
                    slots[idx].val = TValue::Nil();
                    count--;
                    return true;
                }
                matches &= matches - 1;
            }
            if (groups[g].matchEmpty()) return false;
            g = (g + 1) & gMask;
        }
    }

    // Load factor threshold: 87.5% = 14/16 per group
    bool needsRehash() const {
        return capacity == 0 || count >= (capacity * 7 / 8);
    }
};

// ============================================================
// LuaTable — the main table structure
// ============================================================
struct alignas(64) LuaTable {
    // ---- Cache line 0 (hot path fields) ----
    TValue*  array;       // dense array part [0..arraySize-1], 1-indexed logically
    uint32_t arraySize;   // allocated array slots
    uint32_t arrayCount;  // number of non-nil values in array
    HashPart hash;        // Swiss Table hash part
    // ---- Cache line 1+ (cold fields) ----
    LuaTable* metatable;
    uint32_t  flags;      // metamethod cache flags
    uint32_t  gcMark;

    LuaTable() : array(nullptr), arraySize(0), arrayCount(0),
                 metatable(nullptr), flags(0), gcMark(0) {
        hash.groups   = nullptr;
        hash.slots    = nullptr;
        hash.capacity = 0;
        hash.count    = 0;
        hash.numGroups = 0;
    }

    ~LuaTable() {
        if (array)         ::operator delete(array);
        if (hash.capacity) hash.destroy();
    }

    // ================================================================
    // rawget — hot path, should compile to ~10 instructions for
    // the integer-in-array case
    // ================================================================
    ALWAYS_INLINE TValue rawget(TValue key) const {
        // Fast path 1: integer key in array range
        if (LIKELY(key.isInteger())) {
            uint32_t i = (uint32_t)(key.toInteger() - 1); // 0-indexed
            if (LIKELY(i < arraySize))
                return array[i];
            // Fall through to hash
        }
        // Fast path 2: double that is a representable integer
        else if (key.isNumber()) {
            double d = key.toNumber();
            uint32_t i = (uint32_t)(int32_t)d;
            if (LIKELY((double)(int32_t)i == d)) {
                uint32_t ai = i - 1;
                if (LIKELY(ai < arraySize))
                    return array[ai];
                key = TValue::Integer((int32_t)i); // normalize
            }
        }
        // Hash lookup
        TValue* v = hash.find(key);
        return v ? *v : TValue::Nil();
    }

    // ================================================================
    // rawfind — non-mutating lookup, returns pointer or nullptr
    // Used by TableSlotProxy for read access without side effects
    // ================================================================
    ALWAYS_INLINE TValue* rawfind(TValue key) {
        // Integer key in array
        if (key.isInteger()) {
            int32_t i = key.toInteger();
            if (i >= 1 && (uint32_t)i <= arraySize) {
                return array[(uint32_t)(i - 1)].isNil() ? nullptr : &array[(uint32_t)(i - 1)];
            }
        }
        // Normalize double→integer keys
        else if (key.isNumber()) {
            double d = key.toNumber();
            int32_t i = (int32_t)d;
            if ((double)i == d)
                key = TValue::Integer(i);
        }
        // Hash lookup
        return hash.find(key);
    }

    ALWAYS_INLINE const TValue* rawfind(TValue key) const {
        // Integer key in array
        if (key.isInteger()) {
            int32_t i = key.toInteger();
            if (i >= 1 && (uint32_t)i <= arraySize) {
                return array[(uint32_t)(i - 1)].isNil() ? nullptr : &array[(uint32_t)(i - 1)];
            }
        }
        // Normalize double→integer keys
        else if (key.isNumber()) {
            double d = key.toNumber();
            int32_t i = (int32_t)d;
            if ((double)i == d)
                key = TValue::Integer(i);
        }
        // Hash lookup
        return hash.find(key);
    }

    // ================================================================
    // rawset — write key/value, triggers resize if needed
    // ================================================================
    ALWAYS_INLINE void rawset(TValue key, TValue val) {
        assert(!key.isNil()); // Lua: table index is nil → error

        // Fast path: integer key in existing array
        if (LIKELY(key.isInteger())) {
            uint32_t i = (uint32_t)(key.toInteger() - 1);
            if (LIKELY(i < arraySize)) {
                bool wasNil = array[i].isNil();
                array[i] = val;
                if (wasNil && !val.isNil()) arrayCount++;
                else if (!wasNil && val.isNil()) arrayCount--;
                return;
            }
            // Integer key just beyond array — maybe grow array
            if ((int32_t)key.toInteger() == (int32_t)(arraySize + 1) && !val.isNil()) {
                growArray(arraySize + 1);
                array[i] = val;
                arrayCount++;
                return;
            }
        }
        // Normalize double→integer keys
        else if (key.isNumber()) {
            double d = key.toNumber();
            int32_t i = (int32_t)d;
            if ((double)i == d)
                key = TValue::Integer(i);
        }

        // Hash part write
        hashSet(key, val);
    }

    // ================================================================
    // rawsetref — return reference to value slot for assignment
    // Used by operator[] to enable table[key] = value syntax
    // ================================================================
    ALWAYS_INLINE TValue& rawsetref(TValue key) {
        // Fast path: integer key in existing array
        if (LIKELY(key.isInteger())) {
            uint32_t i = (uint32_t)(key.toInteger() - 1);
            if (LIKELY(i < arraySize)) {
                return array[i];
            }
            // Integer key just beyond array — grow array
            if ((int32_t)key.toInteger() == (int32_t)(arraySize + 1)) {
                growArray(arraySize + 1);
                arrayCount++;
                return array[i];
            }
        }
        // Normalize double→integer keys
        else if (key.isNumber()) {
            double d = key.toNumber();
            int32_t i = (int32_t)d;
            if ((double)i == d)
                key = TValue::Integer(i);
        }

        // Hash part write - return reference to slot
        if (UNLIKELY(hash.needsRehash())) {
            uint32_t newCap = (hash.capacity == 0) ? 16 : hash.capacity * 2;
            rebuildHash(newCap);
        }
        TValue* slot = hash.upsert(key);
        return *slot;
    }

    // ================================================================
    // Length operator (#t) — binary search for sequence boundary
    // ================================================================
    uint32_t length() const {
        // Fast path: array is fully packed
        if (arrayCount == arraySize && arraySize > 0 && array[arraySize-1].isNil())
            ; // fall through
        if (arraySize > 0) {
            // Find last non-nil in array using binary search
            if (!array[arraySize-1].isNil()) {
                // Check hash for keys beyond arraySize
                uint32_t j = arraySize + 1;
                while (true) {
                    TValue* v = hash.find(TValue::Integer((int32_t)j));
                    if (!v || v->isNil()) return j - 1;
                    j++;
                }
            }
            // Binary search within array
            uint32_t lo = 0, hi = arraySize;
            while (lo < hi) {
                uint32_t mid = (lo + hi) / 2;
                if (array[mid].isNil()) hi = mid;
                else                    lo = mid + 1;
            }
            return lo; // lo is the length (1-indexed count)
        }
        // Pure hash table: linear probe for integer keys
        uint32_t j = 1;
        while (true) {
            TValue* v = hash.find(TValue::Integer((int32_t)j));
            if (!v || v->isNil()) return j - 1;
            j++;
        }
    }

    // ================================================================
    // next() — table iteration (like lua_next)
    // key = nil → returns first key; key = last → returns nil, nil
    // ================================================================
    bool next(TValue& key, TValue& val) const {
        if (key.isNil()) {
            // Start: find first non-nil array entry
            for (uint32_t i = 0; i < arraySize; i++) {
                if (!array[i].isNil()) {
                    key = TValue::Integer((int32_t)(i + 1));
                    val = array[i];
                    return true;
                }
            }
            // Then hash part
            return nextInHash(~0u, key, val);
        }
        // Advance from current key
        if (key.isInteger()) {
            int32_t ik = key.toInteger();
            if (ik >= 1 && (uint32_t)ik <= arraySize) {
                // Advance in array
                for (uint32_t i = (uint32_t)ik; i < arraySize; i++) {
                    if (!array[i].isNil()) {
                        key = TValue::Integer((int32_t)(i + 1));
                        val = array[i];
                        return true;
                    }
                }
                return nextInHash(~0u, key, val);
            }
        }
        // Find current position in hash and advance
        if (hash.capacity == 0) return false;
        uint32_t startGroup = findHashPos(key);
        return nextInHash(startGroup, key, val);
    }

private:
    // ----------------------------------------------------------------
    // growArray — resize array part to newSize (rounded up to pow2)
    // ----------------------------------------------------------------
    NOINLINE void growArray(uint32_t needed) {
        uint32_t newSize = 16;
        while (newSize < needed) newSize <<= 1;

        TValue* newArr = (TValue*)::operator new(newSize * sizeof(TValue));
        for (uint32_t i = 0; i < newSize; i++) newArr[i] = TValue::Nil();

        if (array) {
            std::memcpy(newArr, array, arraySize * sizeof(TValue));
            ::operator delete(array);
        }
        array     = newArr;
        arraySize = newSize;

        // Pull matching integer keys out of hash into array
        rehashIntegerKeys();
    }

    // ----------------------------------------------------------------
    // rehashIntegerKeys — move integer keys from hash → array after grow
    // ----------------------------------------------------------------
    void rehashIntegerKeys() {
        if (hash.capacity == 0) return;
        for (uint32_t g = 0; g < hash.numGroups; g++) {
            for (uint32_t i = 0; i < 16; i++) {
                if (hash.groups[g].ctrl[i] >= 0) { // live slot
                    uint32_t idx = g * 16 + i;
                    TValue k = hash.slots[idx].key;
                    if (k.isInteger()) {
                        int32_t ik = k.toInteger();
                        uint32_t ai = (uint32_t)(ik - 1);
                        if (ai < arraySize) {
                            array[ai] = hash.slots[idx].val;
                            if (!hash.slots[idx].val.isNil()) arrayCount++;
                            hash.groups[g].ctrl[i] = CTRL_DELETED;
                            hash.slots[idx].val    = TValue::Nil();
                            hash.count--;
                        }
                    }
                }
            }
        }
    }

    // ----------------------------------------------------------------
    // hashSet — write to hash part, growing if necessary
    // ----------------------------------------------------------------
    NOINLINE void hashSet(TValue key, TValue val) {
        if (UNLIKELY(hash.needsRehash())) {
            uint32_t newCap = (hash.capacity == 0) ? 16 : hash.capacity * 2;
            rebuildHash(newCap);
        }
        TValue* slot = hash.upsert(key);
        *slot = val;
        if (val.isNil()) hash.count--; // upsert incremented, but we're deleting
    }

    // ----------------------------------------------------------------
    // rebuildHash — grow & rehash the hash part
    // ----------------------------------------------------------------
    NOINLINE void rebuildHash(uint32_t newCap) {
        HashPart newHash;
        newHash.init(newCap);

        if (hash.capacity > 0) {
            for (uint32_t g = 0; g < hash.numGroups; g++) {
                for (uint32_t i = 0; i < 16; i++) {
                    if (hash.groups[g].ctrl[i] >= 0) {
                        uint32_t idx = g * 16 + i;
                        TValue* slot = newHash.upsert(hash.slots[idx].key);
                        *slot = hash.slots[idx].val;
                    }
                }
            }
            hash.destroy();
        }
        hash = newHash;
    }

    // ----------------------------------------------------------------
    // Iteration helpers
    // ----------------------------------------------------------------
    bool nextInHash(uint32_t afterGroup, TValue& key, TValue& val) const {
        if (hash.capacity == 0) return false;
        uint32_t startG = (afterGroup == ~0u) ? 0 : afterGroup;
        for (uint32_t g = startG; g < hash.numGroups; g++) {
            uint32_t startI = (g == startG && afterGroup != ~0u) ? 1 : 0; // skip current
            for (uint32_t i = startI; i < 16; i++) {
                if (hash.groups[g].ctrl[i] >= 0) {
                    uint32_t idx = g * 16 + i;
                    if (!hash.slots[idx].val.isNil()) {
                        key = hash.slots[idx].key;
                        val = hash.slots[idx].val;
                        return true;
                    }
                }
            }
        }
        return false;
    }

    uint32_t findHashPos(TValue key) const {
        if (hash.capacity == 0) return 0;
        uint32_t h    = hashTValue(key);
        uint32_t g    = hash.h1(h);
        int8_t   h2v  = hash.h2(h);
        uint32_t gMask = hash.numGroups - 1;

        for (;;) {
            uint32_t matches = hash.groups[g].matchH2(h2v);
            while (matches) {
                uint32_t i   = (uint32_t)__builtin_ctz(matches);
                uint32_t idx = g * 16 + i;
                if (hash.slots[idx].key == key) return g;
                matches &= matches - 1;
            }
            if (hash.groups[g].matchEmpty()) return g;
            g = (g + 1) & gMask;
        }
    }

public:
    // ================================================================
    // Convenience wrappers
    // ================================================================
    TValue get(int32_t i) const { return rawget(TValue::Integer(i)); }
    void   set(int32_t i, TValue v) { rawset(TValue::Integer(i), v); }
    TValue get(const char* s) const { return rawget(TValue::String(s)); }
    void   set(const char* s, TValue v) { rawset(TValue::String(s), v); }

    uint32_t hashCount()  const { return hash.count; }
    uint32_t hashCap()    const { return hash.capacity; }
    uint32_t arrSize()    const { return arraySize; }

    // Preallocate (like lua_createtable)
    static LuaTable* create(uint32_t nArr = 0, uint32_t nHash = 0) {
        LuaTable* t = new LuaTable();
        if (nArr > 0) {
            uint32_t cap = 16;
            while (cap < nArr) cap <<= 1;
            t->array     = (TValue*)::operator new(cap * sizeof(TValue));
            t->arraySize = cap;
            for (uint32_t i = 0; i < cap; i++) t->array[i] = TValue::Nil();
        }
        if (nHash > 0) {
            uint32_t cap = 16;
            while (cap < nHash) cap <<= 1;
            t->hash.init(cap);
        }
        return t;
    }
};
inline std::optional<TValue> get_metamethod(TValue a, TValue b, const char* name) {
    // Try a's metatable first (Lua 5.4 precedence)
    if (a.isTable()) {
        if (LuaTable* mt = a.toTable()->metatable) {
            TValue key = TValue::String(name);
            TValue mm = mt->rawget(key);  // rawget, not __index
            if (!mm.isNil()) return mm;
        }
    }
    // Try b's metatable
    if (b.isTable()) {
        if (LuaTable* mt = b.toTable()->metatable) {
            TValue key = TValue::String(name);
            TValue mm = mt->rawget(key);  // rawget, not __index
            if (!mm.isNil()) return mm;
        }
    }
    // No metamethod found
    return std::nullopt;
}

// ============================================================
// TValue arithmetic operator definitions (after get_metamethod)
// ============================================================
ALWAYS_INLINE TValue TValue::operator*(const TValue& o) const {
    if (isTable() || o.isTable()) {
        auto mm = get_metamethod(*this, o, "__mul");
        if (mm) return mm->call(*this, o);
    }
    return Number(asNumber() * o.asNumber());
}
ALWAYS_INLINE TValue TValue::operator+(const TValue& o) const {
    if (isTable() || o.isTable()) {
        auto mm = get_metamethod(*this, o, "__add");
        if (mm) return mm->call(*this, o);
    }
    return Number(asNumber() + o.asNumber());
}
ALWAYS_INLINE TValue TValue::operator-(const TValue& o) const {
    if (isTable() || o.isTable()) {
        auto mm = get_metamethod(*this, o, "__sub");
        if (mm) return mm->call(*this, o);
    }
    return Number(asNumber() - o.asNumber());
}
ALWAYS_INLINE TValue TValue::operator/(const TValue& o) const {
    if (isTable() || o.isTable()) {
        auto mm = get_metamethod(*this, o, "__div");
        if (mm) return mm->call(*this, o);
    }
    return Number(asNumber() / o.asNumber());
}


// ============================================================
// TableSlotProxy — enables correct read/write semantics for operator[]
// ============================================================
struct TableSlotProxy {
    LuaTable* tbl;
    TValue    key;

    // Implicit read: pure lookup, no side effects
    operator TValue() const {
        if (!tbl) return TValue::Nil();
        TValue* p = tbl->rawfind(key);
        return p ? *p : TValue::Nil();
    }
    
    // Implicit conversion to double for return statements
    operator double() const { return static_cast<TValue>(*this).asNumber(); }

    // Write: creates slot on demand
    TableSlotProxy& operator=(TValue val) {
        assert(tbl && "Cannot assign to nil table");
        tbl->rawset(key, val);
        return *this;
    }
    
    TableSlotProxy& operator=(double val) {
        return *this = TValue::Number(val);
    }

    // Copy assignment: reads from rhs, writes through to lhs
    TableSlotProxy& operator=(const TableSlotProxy& other) {
        assert(tbl && "Cannot assign to nil table");
        TValue val = static_cast<TValue>(other);  // Convert rhs to TValue
        tbl->rawset(key, val);  // Write through to lhs's slot
        return *this;
    }

    // Accept callable types and wrap as TValue::Function
    // Handles both:
    //   - Functions matching FuncType signature (TValue(TValue, TValue))
    //   - Simple 0-arg functions (e.g., double()) - wrapped for __index metamethod
    template<typename F, typename = std::enable_if_t<
        std::is_invocable_v<F> && 
        !std::is_same_v<std::decay_t<F>, TValue> &&
        !std::is_same_v<std::decay_t<F>, TableSlotProxy> &&
        !std::is_convertible_v<F, double>
    >>
    TableSlotProxy& operator=(F&& f) {
        if constexpr (std::is_invocable_r_v<TValue, F, TValue, TValue>) {
            // Direct match for FuncType signature
            return *this = TValue::Function(new TValue::FuncType(std::forward<F>(f)));
        } else {
            // Wrap simple functions (0-arg, etc.) for __index metamethod
            auto wrapper = [f = std::forward<F>(f)](TValue, TValue) -> TValue {
                if constexpr (std::is_same_v<std::invoke_result_t<F>, void>) {
                    f();
                    return TValue::Nil();
                } else {
                    return TValue::Number(static_cast<double>(f()));
                }
            };
            return *this = TValue::Function(new TValue::FuncType(std::move(wrapper)));
        }
    }

    // Support chained table access: proxy[k] where proxy is a table slot
    TableSlotProxy operator[](TValue k) const {
        TValue v = static_cast<TValue>(*this);
        return TableSlotProxy{ v.isTable() ? v.toTable() : nullptr, k };
    }
    TableSlotProxy operator[](int32_t k) const {
        return (*this)[TValue::Integer(k)];
    }
    TableSlotProxy operator[](double k) const {
        int32_t i = (int32_t)k;
        if ((double)i == k) return (*this)[TValue::Integer(i)];
        return (*this)[TValue::Number(k)];
    }
    TableSlotProxy operator[](const char* k) const {
        return (*this)[TValue::String(k)];
    }
    
    // Arithmetic operators - delegate to TValue operators (enables metamethod dispatch)
    TValue operator+(const TableSlotProxy& o) const { return static_cast<TValue>(*this) + static_cast<TValue>(o); }
    TValue operator-(const TableSlotProxy& o) const { return static_cast<TValue>(*this) - static_cast<TValue>(o); }
    TValue operator*(const TableSlotProxy& o) const { return static_cast<TValue>(*this) * static_cast<TValue>(o); }
    TValue operator/(const TableSlotProxy& o) const { return static_cast<TValue>(*this) / static_cast<TValue>(o); }
    double operator+(double o) const { return static_cast<TValue>(*this).asNumber() + o; }
    double operator-(double o) const { return static_cast<TValue>(*this).asNumber() - o; }
    double operator*(double o) const { return static_cast<TValue>(*this).asNumber() * o; }
    double operator/(double o) const { return static_cast<TValue>(*this).asNumber() / o; }
    double operator+(int o) const { return static_cast<TValue>(*this).asNumber() + o; }
    double operator-(int o) const { return static_cast<TValue>(*this).asNumber() - o; }
    double operator*(int o) const { return static_cast<TValue>(*this).asNumber() * o; }
    double operator/(int o) const { return static_cast<TValue>(*this).asNumber() / o; }
    
    // Comparison operators
    bool operator==(double o) const { return static_cast<TValue>(*this).asNumber() == o; }
    bool operator!=(double o) const { return static_cast<TValue>(*this).asNumber() != o; }
    bool operator==(int o) const { return static_cast<TValue>(*this).asNumber() == o; }
    bool operator!=(int o) const { return static_cast<TValue>(*this).asNumber() != o; }
    bool operator<(double o) const { return static_cast<TValue>(*this).asNumber() < o; }
    bool operator>(double o) const { return static_cast<TValue>(*this).asNumber() > o; }
    bool operator<=(double o) const { return static_cast<TValue>(*this).asNumber() <= o; }
    bool operator>=(double o) const { return static_cast<TValue>(*this).asNumber() >= o; }
    bool operator<(int o) const { return static_cast<TValue>(*this).asNumber() < o; }
    bool operator>(int o) const { return static_cast<TValue>(*this).asNumber() > o; }
    bool operator<=(int o) const { return static_cast<TValue>(*this).asNumber() <= o; }
    bool operator>=(int o) const { return static_cast<TValue>(*this).asNumber() >= o; }
    
    // Comparison with another TableSlotProxy (disambiguates proxy-to-proxy comparisons)
    bool operator<(TableSlotProxy o) const { return static_cast<TValue>(*this).asNumber() < static_cast<TValue>(o).asNumber(); }
    bool operator>(TableSlotProxy o) const { return static_cast<TValue>(*this).asNumber() > static_cast<TValue>(o).asNumber(); }
    bool operator<=(TableSlotProxy o) const { return static_cast<TValue>(*this).asNumber() <= static_cast<TValue>(o).asNumber(); }
    bool operator>=(TableSlotProxy o) const { return static_cast<TValue>(*this).asNumber() >= static_cast<TValue>(o).asNumber(); }
    bool operator==(TableSlotProxy o) const { return static_cast<TValue>(*this).asNumber() == static_cast<TValue>(o).asNumber(); }
    bool operator!=(TableSlotProxy o) const { return static_cast<TValue>(*this).asNumber() != static_cast<TValue>(o).asNumber(); }
    
    // Unary operators
    double operator-() const { return -static_cast<TValue>(*this).asNumber(); }
    bool operator!() const { return static_cast<TValue>(*this).isFalsy(); }
    
    // Implicit bool conversion for ternary and conditionals
    operator bool() const { return !static_cast<TValue>(*this).isFalsy(); }
    
    // Forward TValue methods for convenience
    double asNumber() const { return static_cast<TValue>(*this).asNumber(); }
    int32_t toInteger() const { return static_cast<TValue>(*this).toInteger(); }
    bool isNil() const { return static_cast<TValue>(*this).isNil(); }
    bool isTable() const { return static_cast<TValue>(*this).isTable(); }
    bool isInteger() const { return static_cast<TValue>(*this).isInteger(); }
    bool isString() const { return static_cast<TValue>(*this).isString(); }
    bool isFalsy() const { return static_cast<TValue>(*this).isFalsy(); }
    LuaTable* toTable() const { return static_cast<TValue>(*this).toTable(); }
    
    // Callable support - enables table["func"](args)
    template<typename... Args>
    TValue operator()(Args&&... args) const {
        TValue func = static_cast<TValue>(*this);
        if (func.isFunction()) {
            // Support 0, 1, or 2 arguments
            if constexpr (sizeof...(args) == 0) {
                return func.call(TValue::Nil(), TValue::Nil());
            } else if constexpr (sizeof...(args) == 1) {
                // Get the single argument and convert to TValue
                auto arg1 = std::get<0>(std::forward_as_tuple(args...));
                return func.call(toTValue(arg1), TValue::Nil());
            } else if constexpr (sizeof...(args) == 2) {
                auto args_tuple = std::forward_as_tuple(args...);
                return func.call(toTValue(std::get<0>(args_tuple)), toTValue(std::get<1>(args_tuple)));
            }
        }
        return TValue::Nil();
    }
    
private:
    // Helper to convert various types to TValue for operator()
    template<typename T>
    static TValue toTValue(T&& val) {
        if constexpr (std::is_same_v<std::decay_t<T>, TValue>) {
            return val;
        } else if constexpr (std::is_same_v<std::decay_t<T>, TableSlotProxy>) {
            return static_cast<TValue>(val);
        } else if constexpr (std::is_same_v<std::decay_t<T>, double>) {
            return TValue::Number(val);
        } else if constexpr (std::is_integral_v<std::decay_t<T>>) {
            return TValue::Integer(static_cast<int32_t>(val));
        } else if constexpr (std::is_same_v<std::decay_t<T>, const char*> || std::is_same_v<std::decay_t<T>, char*>) {
            return TValue::String(val);
        } else if constexpr (std::is_same_v<std::decay_t<T>, LuaTable*>) {
            return TValue::Table(val);
        } else {
            return TValue::Nil();
        }
    }
    
public:
};

// ============================================================
// TValue operator[] — table access for transpiler compatibility
// ============================================================
// Non-const operator[] returns proxy — no side effects until assignment
inline TableSlotProxy TValue::operator[](int32_t index) {
    return TableSlotProxy{ isTable() ? toTable() : nullptr, Integer(index) };
}

inline TValue TValue::operator[](int32_t index) const {
    if (!isTable()) return Nil();
    return toTable()->rawget(Integer(index));
}

inline TableSlotProxy TValue::operator[](double index) {
    int32_t i = (int32_t)index;
    if ((double)i == index) return TableSlotProxy{ isTable() ? toTable() : nullptr, Integer(i) };
    return TableSlotProxy{ isTable() ? toTable() : nullptr, Number(index) };
}

inline TValue TValue::operator[](double index) const {
    if (!isTable()) return Nil();
    int32_t i = (int32_t)index;
    if ((double)i == index) return toTable()->rawget(Integer(i));
    return toTable()->rawget(Number(index));
}

inline TableSlotProxy TValue::operator[](const char* key) {
    return TableSlotProxy{ isTable() ? toTable() : nullptr, String(key) };
}

inline TValue TValue::operator[](const char* key) const {
    if (!isTable()) return Nil();
    return toTable()->rawget(String(key));
}

inline TableSlotProxy TValue::operator[](const std::string& key) {
    return (*this)[key.c_str()];
}

inline TValue TValue::operator[](const std::string& key) const {
    return (*this)[key.c_str()];
}

inline TableSlotProxy TValue::operator[](const TableSlotProxy& key) {
    TValue k = static_cast<TValue>(key);
    if (k.isInteger()) return TableSlotProxy{ isTable() ? toTable() : nullptr, k };
    if (k.isNumber()) {
        double d = k.toNumber();
        int32_t i = (int32_t)d;
        if ((double)i == d)  /* Normalize to integer if whole number */
            return TableSlotProxy{ isTable() ? toTable() : nullptr, Integer(i) };
        return TableSlotProxy{ isTable() ? toTable() : nullptr, k };
    }
    if (k.isString()) return TableSlotProxy{ isTable() ? toTable() : nullptr, k };
    return TableSlotProxy{ nullptr, k };
}


inline TValue TValue::operator[](const TableSlotProxy& key) const {
    if (!isTable()) return Nil();
    TValue k = static_cast<TValue>(key);
    return toTable()->rawget(k);
}

// Assignment from TableSlotProxy (defined after TableSlotProxy is complete)
inline TValue& TValue::operator=(const TableSlotProxy& other) {
    *this = static_cast<TValue>(other);
    return *this;
}

// Comparison operators with TableSlotProxy (fixes heapsort ambiguity)
inline bool TValue::operator<(const TableSlotProxy& o) const {
    return asNumber() < static_cast<TValue>(o).asNumber();
}
inline bool TValue::operator>(const TableSlotProxy& o) const {
    return asNumber() > static_cast<TValue>(o).asNumber();
}
inline bool TValue::operator<=(const TableSlotProxy& o) const {
    return asNumber() <= static_cast<TValue>(o).asNumber();
}
inline bool TValue::operator>=(const TableSlotProxy& o) const {
    return asNumber() >= static_cast<TValue>(o).asNumber();
}

// ============================================================
// Mixed TValue/double arithmetic operators (resolve ambiguity)
// =============================================================
inline double operator*(const TValue& a, double b) { return a.asNumber() * b; }
inline double operator+(const TValue& a, double b) { return a.asNumber() + b; }
inline double operator-(const TValue& a, double b) { return a.asNumber() - b; }
inline double operator/(const TValue& a, double b) { return a.asNumber() / b; }

inline double operator*(double a, const TValue& b) { return a * b.asNumber(); }
inline double operator+(double a, const TValue& b) { return a + b.asNumber(); }
inline double operator-(double a, const TValue& b) { return a - b.asNumber(); }
inline double operator/(double a, const TValue& b) { return a / b.asNumber(); }

// Reverse operators for double * TableSlotProxy
inline double operator*(double a, const TableSlotProxy& b) { return a * static_cast<TValue>(b).asNumber(); }
inline double operator+(double a, const TableSlotProxy& b) { return a + static_cast<TValue>(b).asNumber(); }
inline double operator-(double a, const TableSlotProxy& b) { return a - static_cast<TValue>(b).asNumber(); }
inline double operator/(double a, const TableSlotProxy& b) { return a / static_cast<TValue>(b).asNumber(); }

// ============================================================
// Helper to create callable TValue from lambda
// ============================================================
namespace l2c {
    template<typename F>
    TValue make_function(F&& f) {
        return TValue::Function(new TValue::FuncType(std::forward<F>(f)));
    }
} // namespace l2c

// ============================================================
// END lua_table.hpp
// ============================================================

// Multi-return support for functions returning 2 values
struct MultiReturn2 {
    TValue first;
    TValue second;
    
    MultiReturn2(TValue a, TValue b) : first(a), second(b) {}
    
    // Implicit conversion to TValue (returns first)
    operator TValue() const { return first; }
    
    // Index access for unpacking
    TValue operator[](int i) const { return i == 1 ? first : (i == 2 ? second : TValue::Nil()); }
    TValue operator[](TValue k) const { 
        int i = k.isInteger() ? k.toInteger() : (int)k.asNumber();
        return i == 1 ? first : (i == 2 ? second : TValue::Nil());
    }
};

// Helper to create multi-return
inline MultiReturn2 multi_return(TValue a, TValue b) {
    return MultiReturn2(a, b);
}
