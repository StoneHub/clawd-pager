#pragma once
#include "display_mode_base.h"
#include "listening_mode.h"
#include "processing_mode.h"
#include "agent_mode.h"
// TODO: Include other modes (CONFIRM, AWAITING, DOCKED, QUESTION, RESPONSE, ALERT, IDLE)

// DisplayModeManager - Routes rendering to the appropriate mode class
// Usage in YAML display lambda:
//   DisplayModeManager::render(it, id(display_mode).state, id(pager_display).state);

class DisplayModeManager {
private:
    // Singleton instances of each mode (stateless, reusable)
    static ListeningMode listening_mode;
    static ProcessingMode processing_mode;
    static AgentMode agent_mode;
    // TODO: Add other mode instances

public:
    // Main render dispatcher
    // @param it: ESPHome display buffer
    // @param mode: Current mode string (from display_mode text sensor)
    // @param message: Display text (from pager_display text sensor)
    static void render(esphome::display::DisplayBuffer& it,
                      const std::string& mode,
                      const std::string& message) {

        uint32_t millis = esphome::millis();

        // TODO: YOU IMPLEMENT THIS ROUTING LOGIC
        //
        // Route to the correct mode based on the mode string.
        // Consider:
        // - How to handle unknown modes (default/fallback?)
        // - Whether to use if/else chain or switch/map
        // - How to handle the hybrid approach (some modes in C++, some in YAML)
        //
        // Example pattern:
        // if (mode == "LISTENING") {
        //     listening_mode.render(it, millis, message);
        // } else if (mode == "PROCESSING") {
        //     processing_mode.render(it, millis, message);
        // } ...
        //
        // Or you could keep some modes in YAML and only migrate the animation-heavy ones

        // For now, default to black screen
        it.fill(esphome::Color::BLACK);
    }
};

// Static member initialization
ListeningMode DisplayModeManager::listening_mode;
ProcessingMode DisplayModeManager::processing_mode;
AgentMode DisplayModeManager::agent_mode;
