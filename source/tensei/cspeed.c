/* TenSeiAi C speed module: high-speed top-k temperature sampling.
 *
 * Compiled at build time with the system C compiler
 * (cc/gcc/clang -O2 -shared -fPIC) and called from Python via ctypes.
 * If the compiled library is missing or unloadable, TenSeiAi's numpy
 * sampler is used instead - the C path is a fast optional accelerator. */

#include <stdlib.h>
#include <math.h>

typedef struct {
    float v;
    int i;
} pair_t;

static int cmp_desc(const void *a, const void *b) {
    float va = ((const pair_t *)a)->v;
    float vb = ((const pair_t *)b)->v;
    if (va < vb) return 1;
    if (va > vb) return -1;
    return 0;
}

static unsigned long long rng_state = 88172645463325252ULL;

static double next_double(void) {
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return (double)(rng_state >> 11) / 9007199254740992.0;
}

int tensei_sample(const float *logits, int n, float temperature,
                  int top_k, unsigned long long seed) {
    if (logits == 0 || n <= 0) return -1;
    if (top_k <= 0 || top_k > n) top_k = n;
    pair_t *pairs = (pair_t *)malloc(sizeof(pair_t) * (size_t)n);
    if (pairs == 0) return -1;
    for (int i = 0; i < n; i++) {
        pairs[i].v = logits[i];
        pairs[i].i = i;
    }
    qsort(pairs, (size_t)n, sizeof(pair_t), cmp_desc);
    double t = temperature > 1e-6f ? (double)temperature : 1e-6;
    float mx = pairs[0].v;
    double sum = 0.0;
    for (int i = 0; i < top_k; i++) {
        double e = exp(((double)pairs[i].v - (double)mx) / t);
        pairs[i].v = (float)e;
        sum += e;
    }
    rng_state = seed ? seed : 88172645463325252ULL;
    double target = next_double() * sum;
    double acc = 0.0;
    int pick = pairs[top_k - 1].i;
    for (int i = 0; i < top_k; i++) {
        acc += (double)pairs[i].v;
        if (target <= acc) {
            pick = pairs[i].i;
            break;
        }
    }
    free(pairs);
    return pick;
}

float tensei_dot(const float *a, const float *b, int dim) {
    if (a == 0 || b == 0 || dim <= 0) return 0.0f;
    float sum = 0.0f;
    int i = 0;
    for (; i <= dim - 4; i += 4) {
        sum += a[i] * b[i] + a[i+1] * b[i+1] + a[i+2] * b[i+2] + a[i+3] * b[i+3];
    }
    for (; i < dim; i++) {
        sum += a[i] * b[i];
    }
    return sum;
}

void tensei_dot_batch(const float *query, const float *matrix, float *scores, int n, int dim) {
    if (query == 0 || matrix == 0 || scores == 0 || n <= 0 || dim <= 0) return;
    for (int i = 0; i < n; i++) {
        const float *row = matrix + ((size_t)i * (size_t)dim);
        scores[i] = tensei_dot(query, row, dim);
    }
}
