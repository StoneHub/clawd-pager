#pragma once
#include "display_mode_base.h"

// PROCESSING MODE - Bouncing balls with shadows/glow (Pixar style!)
// Shown when Claude is thinking about a request

class ProcessingMode : public DisplayMode {
public:
    void render(esphome::display::DisplayBuffer& it, uint32_t millis, const std::string& message) override {
        it.fill(esphome::Color::BLACK);
        int frame = (millis / 100) % 20;

        // Rainbow bouncing dots
        esphome::Color dot_colors[] = {
            esphome::Color(255, 50, 50),    // Red
            esphome::Color(255, 150, 0),    // Orange
            esphome::Color(255, 220, 0),    // Yellow
            esphome::Color(100, 255, 50),   // Lime
            esphome::Color(0, 200, 220),    // Cyan
            esphome::Color(100, 100, 255),  // Blue
            esphome::Color(200, 100, 255),  // Purple
            esphome::Color(255, 100, 200)   // Pink
        };

        // Bouncing dots in a wave with shadows and glow
        for (int i = 0; i < 8; i++) {
            int bounce = abs(((frame * 2 + i * 5) % 30) - 15);
            int x = 50 + i * 22;
            int y = 55 + bounce;
            int size = 6 + (bounce / 5);

            // Shadow below (gets bigger when higher)
            int shadow_y = 70;
            int shadow_w = (size + 2) * 2;
            it.filled_rectangle(x - shadow_w / 2, shadow_y, shadow_w, 2, esphome::Color(0, 0, 0, 100));

            // Glow/halo effect
            esphome::Color glow_color = dot_colors[i];
            glow_color.r /= 3; glow_color.g /= 3; glow_color.b /= 3;
            it.filled_circle(x, y, size + 2, glow_color);

            // Main dot
            it.filled_circle(x, y, size, dot_colors[i]);

            // Highlight
            it.filled_circle(x - 1, y - 1, 2, esphome::Color(255, 255, 255));
        }

        // Text labels would need font references - omitted for now
        // In practice, you'll pass fonts to render() or store them as members
    }
};
