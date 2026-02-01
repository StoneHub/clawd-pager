#pragma once
#include "esphome.h"

// Base class for all display modes
// Each mode implements render() to draw its unique animation/UI

class DisplayMode {
public:
    virtual ~DisplayMode() {}

    // Main rendering method - override in each mode
    // @param it: ESPHome display buffer to draw on
    // @param millis: Current uptime in milliseconds (for animations)
    // @param message: Display text from text sensor
    virtual void render(esphome::display::DisplayBuffer& it, uint32_t millis, const std::string& message) = 0;

protected:
    // Shared color palette
    struct Colors {
        static esphome::Color CYAN;
        static esphome::Color TEAL;
        static esphome::Color CORAL;
        static esphome::Color AMBER;
        static esphome::Color LIME;
        static esphome::Color PINK;
        static esphome::Color PURPLE;
        static esphome::Color RED;
        static esphome::Color ORANGE;
        static esphome::Color DIM;
    };

    // Helper: Clean message text (remove control chars)
    std::string clean_text(const std::string& msg) {
        std::string result;
        for (char c : msg) {
            if (c == '\n' || (c >= 32 && c <= 126)) {
                result += c;
            }
        }
        return result;
    }

    // Helper: Word-wrap text to max_chars per line
    std::vector<std::string> word_wrap(const std::string& text, size_t max_chars) {
        std::vector<std::string> lines;
        std::string current_line;

        // Split by paragraphs first (double newlines)
        size_t para_start = 0;
        while (para_start < text.length()) {
            size_t para_end = text.find("\n\n", para_start);
            if (para_end == std::string::npos) para_end = text.length();

            std::string para = text.substr(para_start, para_end - para_start);
            if (!para.empty()) {
                // Word wrap within paragraph
                size_t word_start = 0;
                current_line = "";
                while (word_start < para.length()) {
                    size_t word_end = para.find(' ', word_start);
                    if (word_end == std::string::npos) word_end = para.length();
                    std::string word = para.substr(word_start, word_end - word_start);

                    if (current_line.empty()) {
                        current_line = word;
                    } else if (current_line.length() + 1 + word.length() <= max_chars) {
                        current_line += " " + word;
                    } else {
                        lines.push_back(current_line);
                        current_line = word;
                    }
                    word_start = (word_end == para.length()) ? word_end : word_end + 1;
                }
                if (!current_line.empty()) lines.push_back(current_line);
            }
            para_start = para_end + 2; // Skip \n\n
        }
        return lines;
    }
};

// Define colors (implementation)
esphome::Color DisplayMode::Colors::CYAN = esphome::Color(0, 255, 255);
esphome::Color DisplayMode::Colors::TEAL = esphome::Color(0, 200, 200);
esphome::Color DisplayMode::Colors::CORAL = esphome::Color(255, 127, 80);
esphome::Color DisplayMode::Colors::AMBER = esphome::Color(255, 191, 0);
esphome::Color DisplayMode::Colors::LIME = esphome::Color(50, 205, 50);
esphome::Color DisplayMode::Colors::PINK = esphome::Color(255, 105, 180);
esphome::Color DisplayMode::Colors::PURPLE = esphome::Color(147, 112, 219);
esphome::Color DisplayMode::Colors::RED = esphome::Color(255, 60, 60);
esphome::Color DisplayMode::Colors::ORANGE = esphome::Color(255, 140, 0);
esphome::Color DisplayMode::Colors::DIM = esphome::Color(100, 100, 100);
