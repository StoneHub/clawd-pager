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

        // Route animation-heavy modes to C++ classes.
        // Returns true if handled, false if YAML should render instead.
        if (mode == "LISTENING") {
            listening_mode.render(it, millis, message);
        } else if (mode == "PROCESSING") {
            processing_mode.render(it, millis, message);
        } else if (mode == "AGENT") {
            agent_mode.render(it, millis, message);
        } else {
            // Not handled — caller (YAML lambda) should render this mode
            return false;
        }
        return true;
    }
};

// Static member initialization
ListeningMode DisplayModeManager::listening_mode;
ProcessingMode DisplayModeManager::processing_mode;
AgentMode DisplayModeManager::agent_mode;
