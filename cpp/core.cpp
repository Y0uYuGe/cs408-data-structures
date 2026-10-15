// C++17 counterpart: ownership, KMP, heap sort, and BFS; fixtures mirror Python tests.
#include <cassert>
#include <cstddef>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

template <class T> class Sequence {
    T* data_;
    std::size_t size_ = 0, capacity_ = 4;
public:
    Sequence() : data_(new T[4]) {}
    ~Sequence() { delete[] data_; }
    Sequence(const Sequence&) = delete;  // no accidental double free
    Sequence& operator=(const Sequence&) = delete;
    void push(const T& value) {
        if (size_ == capacity_) {
            T* next = new T[capacity_ * 2];
            for (std::size_t i = 0; i < size_; ++i) next[i] = data_[i];
            delete[] data_; data_ = next; capacity_ *= 2;
        }
        data_[size_++] = value;
    }
    T pop() { if (!size_) throw std::out_of_range("empty"); return data_[--size_]; }
    T& operator[](std::size_t i) { if (i >= size_) throw std::out_of_range("index"); return data_[i]; }
    std::size_t size() const { return size_; }
};

std::size_t kmp(const std::string& text, const std::string& pattern) {
    if (pattern.empty()) return 0;
    std::vector<std::size_t> prefix(pattern.size(), 0);
    for (std::size_t i = 1, j = 0; i < pattern.size(); ++i) {
        while (j && pattern[i] != pattern[j]) j = prefix[j - 1];
        if (pattern[i] == pattern[j]) ++j;
        prefix[i] = j;
    }
    for (std::size_t i = 0, j = 0; i < text.size(); ++i) {
        while (j && text[i] != pattern[j]) j = prefix[j - 1];
        if (text[i] == pattern[j]) ++j;
        if (j == pattern.size()) return i - j + 1;
    }
    return std::string::npos;
}

void sift(std::vector<int>& a, std::size_t root, std::size_t n) {
    while (root * 2 + 1 < n) {
        std::size_t child = root * 2 + 1;
        if (child + 1 < n && a[child] < a[child + 1]) ++child;
        if (a[root] >= a[child]) break;
        std::swap(a[root], a[child]); root = child;
    }
}
void heap_sort(std::vector<int>& a) {
    for (std::size_t i = a.size() / 2; i > 0; --i) sift(a, i - 1, a.size());
    for (std::size_t n = a.size(); n > 1; --n) { std::swap(a[0], a[n - 1]); sift(a, 0, n - 1); }
}
std::vector<int> bfs(const std::vector<std::vector<int>>& adj, int source) {
    if (source < 0 || static_cast<std::size_t>(source) >= adj.size()) throw std::out_of_range("source");
    std::vector<int> distance(adj.size(), -1), queue;
    distance[source] = 0; queue.push_back(source);
    for (std::size_t head = 0; head < queue.size(); ++head) {
        const int a = queue[head];
        for (int b : adj[a]) if (distance[b] < 0) { distance[b] = distance[a] + 1; queue.push_back(b); }
    }
    return distance;
}
int main() {
    Sequence<int> s;
    for (int i = 0; i < 100; ++i) s.push(i);
    assert(s.size() == 100 && s[50] == 50 && s.pop() == 99);
    assert(kmp("ababababaca", "ababaca") == 4);
    assert(kmp("abc", "") == 0 && kmp("abc", "x") == std::string::npos);
    // std::string positions are UTF-8 byte offsets, unlike Python Unicode code-point offsets.
    assert(kmp("数据结构", "结构") == 6);
    std::vector<int> values = {3, -1, 8, 3, 0}; heap_sort(values);
    assert((values == std::vector<int>{-1, 0, 3, 3, 8}));
    std::vector<int> empty; heap_sort(empty); assert(empty.empty());
    assert((bfs({{1, 2}, {0, 3}, {0}, {1}, {}}, 0) == std::vector<int>{0, 1, 1, 2, -1}));
    std::cout << "C++17 core assertions passed\n";
}
