#pragma once
#include "display_mode_base.h"

// LISTENING MODE - Rainbow waveform animation
// Shown when user holds Button A for voice recording

class ListeningMode : public DisplayMode {
public:
    void render(esphome::display::DisplayBuffer& it, uint32_t millis, const std::string& message) override {
        it.fill(esphome::Color::BLACK);
        int frame = (millis / 100) % 20;  // Animation frame

        // Rainbow colors for waveform bars
        esphome::Color rainbow[] = {
            esphome::Color(255, 50, 50),    // Red
            esphome::Color(255, 150, 0),    // Orange
            esphome::Color(255, 220, 0),    // Yellow
            esphome::Color(100, 255, 50),   // Lime
            esphome::Color(0, 220, 180),    // Teal
            esphome::Color(50, 150, 255),   // Blue
            esphome::Color(150, 100, 255),  // Purple
            esphome::Color(255, 100, 200),  // Pink
            esphome::Color(255, 150, 0),    // Orange
            esphome::Color(255, 220, 0),    // Yellow
            esphome::Color(100, 255, 50),   // Lime
            esphome::Color(0, 220, 180)     // Teal
        };

        // Bouncy rainbow waveform
        for (int i = 0; i < 12; i++) {
            int phase = (frame + i * 3) % 20;
            int h = 10 + abs(10 - phase) * 3;
            it.filled_rectangle(25 + i * 17, 68 - h, 12, h * 2, rainbow[i]);
        }

        // Cute bouncing mic icon (circle with lines)
        int bounce = abs((frame % 10) - 5);
        it.filled_circle(120, 115 + bounce, 8, esphome::Color::WHITE);
        it.filled_rectangle(117, 123 + bounce, 6, 8, esphome::Color::WHITE);
    }
};
