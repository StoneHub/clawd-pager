#pragma once
#include "display_mode_base.h"
#include <cmath>

// AGENT MODE - Matrix-style code rain with bouncing ball
// Shown when Claude Code is actively using tools

class AgentMode : public DisplayMode {
public:
    void render(esphome::display::DisplayBuffer& it, uint32_t millis, const std::string& message) override {
        it.fill(esphome::Color::BLACK);
        int code_frame = (millis / 80) % 40;  // Fast animation

        // Matrix-style falling code effect
        for (int col = 0; col < 12; col++) {
            int offset = (col * 7 + code_frame * 3) % 40;
            for (int row = 0; row < 6; row++) {
                int y = (row * 22 + offset) % 135;
                int brightness = 255 - (row * 40);
                if (brightness < 50) brightness = 50;
                esphome::Color code_color = esphome::Color(0, brightness, brightness / 2);

                // Random "characters" (just rectangles of varying sizes)
                int char_w = 3 + ((col + row + code_frame) % 4);
                it.filled_rectangle(20 + col * 18, y, char_w, 8, code_color);
            }
        }

        // Agent status overlay
        it.filled_rectangle(40, 45, 160, 50, esphome::Color(0, 0, 0));
        it.rectangle(40, 45, 160, 50, Colors::CYAN);

        // Bouncing ball animation (Pixar style!)
        float ball_time = (millis % 1200) / 1200.0;  // 1.2s cycle
        float bounce_height;

        if (ball_time < 0.5) {
            // Going up (ease out)
            float t = ball_time * 2.0;
            bounce_height = 1.0 - (1.0 - t) * (1.0 - t);
        } else {
            // Coming down (ease in)
            float t = (ball_time - 0.5) * 2.0;
            bounce_height = 1.0 - t * t;
        }

        int ball_y = 108 - (int)(bounce_height * 25);

        // Ball squash and stretch
        int ball_radius = 6;
        int ball_w_scale = 0;
        if (ball_y > 100) {
            // Squashed at bottom
            ball_w_scale = 2;
            ball_radius = 4;
        }

        // Shadow
        int shadow_w = 10 + (108 - ball_y) / 3;
        it.filled_rectangle(115 - shadow_w / 2, 110, shadow_w, 2, esphome::Color(0, 0, 0, 100));

        // Ball glow
        it.filled_circle(115, ball_y, ball_radius + 2 + ball_w_scale, esphome::Color(0, 100, 100));

        // Ball
        it.filled_circle(115, ball_y, ball_radius + ball_w_scale, Colors::CYAN);
        it.filled_circle(115 - 1, ball_y - 1, 2, esphome::Color(255, 255, 255));

        // Text rendering would require font references
        // In a full implementation, pass fonts to render() or make them members
    }
};
