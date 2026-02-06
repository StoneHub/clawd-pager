#pragma once
#include "display_mode_base.h"
#include "listening_mode.h"
#include "processing_mode.h"
#include "agent_mode.h"

// DisplayModeManager - Routes rendering to the appropriate C++ mode class.
// Handles animation-heavy modes in C++; returns false for modes that
// should be rendered by YAML lambdas (text-heavy, font-dependent).
//
// Usage in YAML display lambda:
//   if (!DisplayModeManager::render(it, id(display_mode).state, id(pager_display).state)) {
//       // ... existing YAML rendering for this mode ...
//   }

class DisplayModeManager {
private:
    static ListeningMode listening_mode;
    static ProcessingMode processing_mode;
    static AgentMode agent_mode;

public:
    // Returns true if mode was rendered by C++, false if YAML should handle it.
    static bool render(esphome::display::DisplayBuffer& it,
                      const std::string& mode,
                      const std::string& message) {

        uint32_t millis = esphome::millis();

        // Route modes to C++ classes where feature-complete.
        // PROCESSING and AGENT still need font support for text labels,
        // so they stay in YAML for now.
        if (mode == "LISTENING") {
            listening_mode.render(it, millis, message);
            return true;
        }

        // Future: uncomment when font passing is implemented
        // if (mode == "PROCESSING") { processing_mode.render(...); return true; }
        // if (mode == "AGENT") { agent_mode.render(...); return true; }

        return false;
    }
};

// Static member initialization
ListeningMode DisplayModeManager::listening_mode;
ProcessingMode DisplayModeManager::processing_mode;
AgentMode DisplayModeManager::agent_mode;
