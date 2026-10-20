// TenSeiAi C++ client (C++17, POSIX sockets, no dependencies).
// build: g++ -O2 -std=c++17 tensei_client.cpp -o tensei_client && ./tensei_client "hello"
#include <arpa/inet.h>
#include <netdb.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <thread>

static std::string http(const std::string &method, const std::string &path,
                        const std::string &body) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(8765);
    inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr);
    if (fd < 0 || connect(fd, (sockaddr *)&addr, sizeof(addr)) != 0) {
        std::cerr << "TenSeiAi not running on 127.0.0.1:8765\n";
        return "";
    }
    std::ostringstream req;
    req << method << " " << path << " HTTP/1.1\r\nHost: 127.0.0.1:8765\r\n"
        << "Content-Type: application/json\r\nContent-Length: " << body.size()
        << "\r\nConnection: close\r\n\r\n" << body;
    std::string r = req.str();
    send(fd, r.data(), r.size(), 0);
    std::string out;
    char buf[8192];
    ssize_t n;
    while ((n = recv(fd, buf, sizeof(buf), 0)) > 0) out.append(buf, (size_t)n);
    close(fd);
    return out;
}

static std::string jsonStr(const std::string &s, const std::string &key) {
    std::string needle = "\"" + key + "\": \"";
    size_t start = s.find(needle);
    if (start == std::string::npos) return "";
    start += needle.size();
    std::string out;
    for (size_t i = start; i < s.size(); ++i) {
        if (s[i] == '\\' && i + 1 < s.size()) { out += s[++i]; continue; }
        if (s[i] == '"') break;
        out += s[i];
    }
    return out;
}

int main(int argc, char **argv) {
    std::string q = argc > 1 ? argv[1] : "hello";
    if (argc > 2)
        for (int i = 2; i < argc; ++i) q += std::string(" ") + argv[i];
    for (size_t i = 0; i < q.size(); ++i)
        if (q[i] == '"') q.insert(i, 1, '\\'), ++i;
    std::string job = http("POST", "/api/ask", "{\"q\": \"" + q + "\"}");
    std::string id = jsonStr(job, "id");
    if (id.empty()) return 1;
    for (int i = 0; i < 600; ++i) {
        std::string j = http("GET", "/api/job?id=" + id, "");
        if (j.find("\"status\": \"done\"") != std::string::npos) {
            std::cout << jsonStr(j, "answer") << "\n";
            return 0;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
    }
    std::cerr << "(timeout)\n";
    return 1;
}
