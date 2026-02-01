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

## What's Been Done

- ✅ Base architecture (DisplayMode abstract class)
- ✅ ListeningMode (rainbow waveform)
- ✅ ProcessingMode (bouncing balls)
- ✅ AgentMode (matrix code rain)
- ⏳ DisplayModeManager routing logic (TODO: you implement)
- ⏳ Remaining modes (CONFIRM, QUESTION, RESPONSE, ALERT, IDLE, AWAITING, DOCKED)

## Next Steps - YOU DECIDE

### Decision 1: Routing Logic
In `display_mode_manager.h`, implement the `render()` method's mode routing.

Consider:
- **Simple if/else chain**: Easy to understand, linear search
- **Map-based dispatch**: O(1) lookup, more complex setup
- **Fallback handling**: What happens if mode is unknown?

### Decision 2: Font Strategy
How should modes access fonts defined in YAML?

- **Pass as parameters**: `render(it, millis, msg, font_body, font_large, ...)`
- **Global setter**: `set_fonts()` called once at init
- **Hybrid**: Keep text rendering in YAML, C++ only for animations

### Decision 3: Migration Scope
Should we migrate ALL 9 modes to C++, or just the animation-heavy ones?

- **Full migration**: Consistent, fully testable, but more work
- **Selective**: Migrate LISTENING, PROCESSING, AGENT (done), keep simple modes in YAML
- **Incremental**: Migrate one per week as needed

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

**Your turn!** Open `display_mode_manager.h` and implement the routing logic in the `render()` method. Decide which approach fits your workflow best.
