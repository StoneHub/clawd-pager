# Clawd Pager - UX Improvement Backlog

Ideas for iterative improvements, sorted by impact/effort ratio.

## High Priority (Big Impact, Low Effort)

### 1. Notification History
- **What**: Swipe through recent messages with Button B
- **Why**: See what you missed if you looked away
- **How**: Ring buffer of last 10 messages, Button B cycles through

### 2. Quick Actions Menu
- **What**: Long-press Button A (3s) opens quick menu
- **Why**: Access common functions without voice
- **How**: Menu shows: Status / Clear / Sleep / Reboot

### 3. Battery-Aware Animations
- **What**: Simpler animations when battery < 20%
- **Why**: Extend battery life when low
- **How**: Disable bouncing ball, use static icons instead

### 4. Custom Ringtones per Source
- **What**: Different sounds for Claude Code vs Clawdbot
- **Why**: Know who's calling without looking
- **How**:
  - Claude Code: Tech beeps (current)
  - Clawdbot: Friendly chirp
  - Alert: Urgent buzz

### 5. Time-Based Auto-Brightness
- **What**: Dimmer at night (10pm-6am)
- **Why**: Don't blind yourself at 2am
- **How**: Check time, reduce backlight 50% during night hours

## Medium Priority (Good Impact, Medium Effort)

### 6. Network Status Indicator
- **What**: WiFi icon shows signal strength
- **Why**: Know if disconnects are network issues
- **How**: Color-coded bars: Green (strong), Amber (weak), Red (poor)

### 7. Gesture Controls
- **What**: Shake to wake from sleep, tilt to scroll
- **Why**: More intuitive interaction
- **How**: Use IMU (MPU6886) for accelerometer input
- **Note**: M5StickC Plus has IMU, needs enabling

### 8. Voice Feedback (TTS)
- **What**: Speak responses, not just display
- **Why**: Hands-free operation while working
- **How**: Use ESP32 DAC + simple phoneme synthesis OR stream from Pi
- **Challenge**: Limited audio quality on tiny buzzer

### 9. OTA Update Progress Bar
- **What**: Visual progress during firmware updates
- **Why**: Know it's working, not frozen
- **How**: Hook into ESPHome OTA events, show % bar

### 10. Screenshot/Log Capture
- **What**: Button combo (A+B together) saves screen to SD or sends to Pi
- **Why**: Debug display issues, share status
- **How**: Capture framebuffer, send via ESPHome API

## Low Priority (Nice to Have)

### 11. Themes (Day/Night/High Contrast)
- **What**: Color scheme presets
- **Why**: Accessibility, preference
- **How**: Global color palette swap

### 12. Calendar Integration
- **What**: Show next meeting on IDLE screen
- **Why**: Useful ambient info
- **How**: Already have `gog` - just parse and display

### 13. Multi-Language Support
- **What**: Display in Spanish/French/etc
- **Why**: Accessibility
- **How**: String table with language selector

### 14. Docked Mode Enhancements
- **What**: Act as secondary monitor when on desk
- **Why**: Persistent status display
- **How**: Show git branch, time tracking, pomodoro timer

### 15. Haptic Feedback
- **What**: Vibration motor for alerts
- **Why**: Silent notifications
- **How**: Requires hardware mod (M5StickC doesn't have vibration motor)
- **Note**: Could use buzzer in very brief pulses as pseudo-haptic

## Advanced (Ambitious)

### 16. Voice Commands Beyond Yes/No
- **What**: "Snooze 5 minutes", "Show calendar", "Check battery"
- **Why**: Truly hands-free
- **How**: Local keyword spotting or full Whisper STT

### 17. Companion App
- **What**: Phone app to configure pager
- **Why**: Easier than YAML editing
- **How**: ESPHome web server + responsive UI

### 18. Agent Marketplace
- **What**: Community agents you can call from pager
- **Why**: Extend functionality
- **How**: Plugin system, agent registry

### 19. Context-Aware Responses
- **What**: Pager suggests answers based on question type
- **Why**: Faster decision making
- **How**: Simple NLP on Pi, highlight recommended choice

### 20. Multi-Pager Support
- **What**: Multiple M5StickC devices, different roles
- **Why**: One for Claude, one for notifications, one for music
- **How**: Bridge routes to specific device IDs

## Implementation Strategy

Pick ONE per session:
1. Choose from High Priority
2. Implement in ~1 hour
3. Test immediately
4. Git commit
5. Move to next

## Current Iteration Ideas

- [ ] Notification history (ring buffer)
- [ ] Battery-aware animations
- [ ] Custom ringtones per source
- [ ] Quick actions menu

## Completed

- [x] Text wrapping (24 chars)
- [x] Auto-scrolling long questions
- [x] Pixar-style animations
- [x] Blinking robot eyes
- [x] Button redesign (A=YES, B=NO)
- [x] Voice capture with confirmation
- [x] Claude Code hooks integration
