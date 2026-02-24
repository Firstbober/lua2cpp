#include <iostream>
#include <cmath>
#include <iomanip>

struct Complex {
    double re;
    double im;
    Complex(double r, double i) : re(r), im(i) {}
    Complex operator*(const Complex& other) const {
        return Complex(re * other.re - im * other.im, re * other.im + im * other.re);
    }
    Complex operator+(const Complex& other) const {
        return Complex(re + other.re, im + other.im);
    }
    double abs() const {
        return std::sqrt(re * re + im * im);
    }
};

template<typename T1, typename T2>
auto level(T1 x, T2 y) {
    Complex c(x, y);
    Complex z(0, 0);
    int l = 0;
    for (int i = 0; i < 1000; i++) {
        auto prod = z * z;
        z = prod + c;
        l = (l + 1);
        if (z.abs() >= 2.0 || l > 255) {
            break;
        }
    }
    return (l - 1);
}

int main() {
    double xmin = -2.0;
    double xmax = 2.0;
    double ymin = -2.0;
    double ymax = 2.0;
    int N = 10;
    double dx = (xmax - xmin) / N;
    double dy = (ymax - ymin) / N;

    std::cout << "P2" << std::endl;
    std::cout << "# mandelbrot set\t" << xmin << "\t" << xmax << "\t" << ymin << "\t" << ymax << "\t" << N << std::endl;
    std::cout << N << "\t" << N << "\t255" << std::endl;

    int S = 0;
    for (int i = 1; i <= N; i++) {
        double x = xmin + ((i - 1) * dx);
        for (int j = 1; j <= N; j++) {
            double y = ymin + ((j - 1) * dy);
            S = (S + level(x, y));
        }
    }
    std::cout << S << std::endl;

    return 0;
}
