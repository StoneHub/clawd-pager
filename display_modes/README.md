# Display Modes C++ Refactoring

## Architecture

Instead of 700+ lines of inline C++ lambdas in `clawd-pager.yaml`, we've extracted display rendering into reusable, testable C++ components.

## Structure

```
display_modes/
├── display_mode_base.h      # Base class, shared utilities, color palette
├── listening_mode.h          # Rainbow waveform animation
├── processing_mode.h         # Bouncing balls with shadows
├── agent_mode.h              # Matrix code rain + bouncing ball
├── display_mode_manager.h    # Routes mode string → correct renderer
└── README.md                 # This file
```

## Integration with ESPHome YAML

### Option 1: Full C++ (Clean but requires font passing)

```yaml
display:
  - platform: st7789v
    # ...
    lambda: |-
      DisplayModeManager::render(it, id(display_mode).state, id(pager_display).state);
```

**Pros**: Minimal YAML, everything testable
**Cons**: Need to solve font passing (fonts defined in YAML, used in C++)

### Option 2: Hybrid (Animations in C++, Text in YAML)

```yaml
display:
  - platform: st7789v
    lambda: |-
      std::string mode = id(display_mode).state;
      std::string msg = id(pager_display).state;

      // Render animations via C++
      if (mode == "LISTENING" || mode == "PROCESSING" || mode == "AGENT") {
        DisplayModeManager::render(it, mode, msg);
      } else {
        // Keep other modes in YAML (RESPONSE, QUESTION, etc.)
        // ... existing YAML code for text-heavy modes ...
      }
```

**Pros**: Incremental migration, no font issues
**Cons**: Split brain (some logic in C++, some in YAML)

### Option 3: Full C++ with Global Font Refs

```yaml
esphome:
  includes:
    - display_modes/

display:
  - platform: st7789v
    lambda: |-
      // Make fonts globally accessible
      DisplayModeManager::set_fonts(&id(font_body), &id(font_large), &id(font_small));
      DisplayModeManager::render(it, id(display_mode).state, id(pager_display).state);
```

**Pros**: Full C++ control, testable
**Cons**: Fonts as globals (not ideal, but pragmatic)

## Status

- ✅ Base architecture (DisplayMode abstract class)
- ✅ ListeningMode (rainbow waveform)
- ✅ ProcessingMode (bouncing balls)
- ✅ AgentMode (matrix code rain)
- ✅ DisplayModeManager routing — returns `bool` (true = handled by C++, false = YAML should render)
- ⏳ Remaining modes (CONFIRM, QUESTION, RESPONSE, ALERT, IDLE, AWAITING, DOCKED) — staying in YAML for now

## Decisions Made

### Routing Logic
Simple if/else chain with `bool` return. C++ handles animation-heavy modes; YAML handles text/font-dependent modes. This is the **hybrid approach**.

### Font Strategy
**Hybrid**: Animations stay in C++ (no fonts needed), text rendering stays in YAML (has font access). When/if we migrate text modes to C++, use a global font setter.

### Migration Scope
**Selective/incremental**: Only animation-heavy modes (LISTENING, PROCESSING, AGENT) are in C++. Text-heavy modes with font dependencies (QUESTION, PERMISSION, AGENT_EDIT, etc.) stay in YAML until a font-passing mechanism is needed.

## Testing (Future)

Once modes are in C++, we can write unit tests:

```cpp
TEST(ListeningModeTest, RendersRainbowBars) {
    MockDisplayBuffer buffer;
    ListeningMode mode;
    mode.render(buffer, 1000, "");
    EXPECT_EQ(buffer.rectangle_count(), 12);  // 12 rainbow bars
}
```

This is impossible with YAML lambdas.

## Trade-offs Summary

| Approach | Testability | Complexity | Iteration Speed | Text Rendering |
|----------|-------------|------------|-----------------|----------------|
| Full C++ | ⭐⭐⭐⭐⭐ | Medium | ⭐⭐⭐⭐ | Need font solution |
| Hybrid | ⭐⭐⭐ | Low | ⭐⭐⭐⭐⭐ | Easy (stay in YAML) |
| Current (YAML) | ⭐ | Low | ⭐⭐ | Easy |

---

## Wiring Into YAML

To activate the C++ renderer, add this guard at the top of the display lambda in `clawd-pager.yaml`:

```yaml
# After: std::string mode = id(display_mode).state;
# After: std::string msg = id(pager_display).state;
if (DisplayModeManager::render(it, mode, msg)) return;
```

This lets C++ handle LISTENING/PROCESSING/AGENT (returning `true`), and falls through to the existing YAML mode handlers for everything else.
