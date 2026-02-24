#include <iostream>
#include <cmath>
#include <iomanip>

using namespace std;

// Table-based Complex operations (matching generated code)
struct ComplexTable {
    double re, im;
    ComplexTable(double r, double i) : re(r), im(i) {}
    
    // Helper functions
    static ComplexTable mul(ComplexTable x, ComplexTable y) {
        return ComplexTable(x.re * y.re - x.im * y.im, x.re * y.im + x.im * y.re);
    }
    
    static ComplexTable add(ComplexTable x, ComplexTable y) {
        return ComplexTable(x.re + y.re, x.im + y.im);
    }
    
    static ComplexTable conj(ComplexTable x) {
        return ComplexTable(x.re, -x.im);
    }
    
    static double norm2(ComplexTable x) {
        ComplexTable n = mul(x, conj(x));
        return n.re;
    }
    
    static double abs(ComplexTable x) {
        return sqrt(norm2(x));
    }
    
    static ComplexTable make(double r, double i) {
        return ComplexTable(r, i);
    }
};

// Level function matching generated code
template<typename T1, typename T2>
int level(T1 x, T2 y) {
    ComplexTable c = ComplexTable::make(x, y);
    ComplexTable z = ComplexTable::make(0, 0);
    int l = 0;
    for (int i = 0; i < 1000; i++) {
        z = ComplexTable::add(ComplexTable::mul(z, z), c);
        l = l + 1;
        if (ComplexTable::abs(z) >= 2.0 || l > 255) {
            break;
        }
    }
    return l - 1;
}

int main() {
    double xmin = -2.0, xmax = 2.0, ymin = -2.0, ymax = 2.0;
    int N = 10;
    double dx = (xmax - xmin) / N;
    double dy = (ymax - ymin) / N;

    cout << "P2" << endl;
    cout << "# mandelbrot set\t" << xmin << "\t" << xmax << "\t" << ymin << "\t" << ymax << "\t" << N << endl;
    cout << N << "\t" << N << "\t255" << endl;

    int S = 0;
    for (int i = 1; i <= N; i++) {
        double x = xmin + ((i - 1) * dx);
        for (int j = 1; j <= N; j++) {
            double y = ymin + ((j - 1) * dy);
            S = S + level(x, y);
        }
    }
    cout << S << endl;

    return 0;
}
