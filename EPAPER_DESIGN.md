# Clawd Pager - ePaper Edition Design

**Target Hardware**: ESP32-S3-ePaper-1.54 (200x200 pixels)
**Display Type**: ePaper (high contrast, sunlight readable)
**Focus**: Maximum information density + human readability

---

## Design Philosophy

### Why ePaper is Perfect for Dense Information

1. **Crisp Text**: Black/white contrast → no color bleed, sharp edges
2. **Sunlight Readable**: No backlight glare, readable anywhere
3. **Low Power**: Only draws power during refresh (can show persistent dashboards)
4. **200x200 Resolution**: 40% more pixels than M5 (135x240) → fit more data

### Information Density Strategy

**M5StickC Plus (135x240 TFT)**:
- Large colorful animations
- 1-2 lines of text per screen
- Emphasis on "glanceability"

**ESP32-S3 ePaper (200x200)**:
- Dashboard-style layouts
- 4-6 sections of data per screen
- Readable text down to 10-12px
- Persistent display (no need to constantly refresh)

---

## Screen Layouts

### 1. DASHBOARD Mode (Default)

```
┌────────────────────────────────┐
│ 14:23              Battery 85% │ ← Header (30px)
├────────────────────────────────┤
│ AGENT: Editing files...        │
│ Tool: grep_files               │ ← Agent Status (50px)
├────────────────────────────────┤
│ TASKS:                         │
│ • Awaiting approval            │
│ • 2 notifications pending      │ ← Task Queue (60px)
├────────────────────────────────┤
│ WIFI: ClawdNet                 │
│ IP: 192.168.50.85              │
│ Uptime: 4h 23m                 │ ← System Info (60px)
└────────────────────────────────┘
```

**Data Density**: 6+ data points visible at once
**Refresh Rate**: 30 seconds (ePaper doesn't need constant updates)

---

### 2. QUESTION Mode (Approval Prompts)

```
┌────────────────────────────────┐
│ 14:23              Battery 85% │
├────────────────────────────────┤
│                                │
│           ❓                    │
│                                │
│   Delete 5 files?              │
│                                │
│   /home/monroe/test.txt        │
│   /home/monroe/old.log         │
│   ...and 3 more                │
│                                │
├────────────────────────────────┤
│    [YES]            [NO]       │
└────────────────────────────────┘
```

**Focus**: Clear question + context details
**Action**: Two-button approval (YES/NO)

---

### 3. CALENDAR/AGENDA Mode

```
┌────────────────────────────────┐
│ 14:23              Battery 85% │
├────────────────────────────────┤
│ TODAY - Mon Feb 10             │
│                                │
│ 09:00  Morning standup         │
│ 14:00  Code review             │
│ 16:30  Deploy to prod          │
│                                │
│ TOMORROW - Tue Feb 11          │
│ 10:00  Client meeting          │
│                                │
└────────────────────────────────┘
```

**Data Density**: 5-6 events visible
**Refresh**: Every 5 minutes or on demand

---

### 4. SYSTEM MONITOR Mode

```
┌────────────────────────────────┐
│ fcfdev - 14:23     Battery 85% │
├────────────────────────────────┤
│ CPU: ████████░░ 80%            │
│ MEM: ██████░░░░ 60%            │
│ DSK: ███░░░░░░░ 30%            │
│                                │
│ SERVICES:                      │
│ ✓ clawd-bridge                 │
│ ✓ clawdbot                     │
│ ✗ nginx (stopped)              │
│                                │
│ NETWORK: 192.168.50.50         │
└────────────────────────────────┘
```

**Use Case**: Quick system health check
**Refresh**: 60 seconds

---

## Typography Strategy

### Font Choice: Roboto Mono

**Why Monospace?**
- Aligns data in columns
- Predictable spacing for dashboards
- Highly readable at small sizes
- Works great on black/white ePaper

### Font Sizes

| Size | Use Case | Line Height |
|------|----------|-------------|
| 10px | Dense tables, system info | 12px |
| 12px | Body text, list items | 14px |
| 16px | Headers, emphasis | 18px |
| 24px | Large icons, questions | 28px |

**Glyphs**: Include emoji/icons for visual markers (✓✗❓🎤⚙️)

---

## Layout Grid

```
200px width ÷ 5 columns = 40px each
200px height ÷ 6 rows = 33px each

Grid helps align:
- Text blocks
- Buttons
- Sections
- Icons
```

**Margins**: 5px all around
**Section dividers**: 1px horizontal lines
**Readable width**: ~190px (leave 5px margins)

---

## Button Mapping (Same as M5)

| Button | Short Press | Long Hold |
|--------|-------------|-----------|
| **A** | Yes / Status | Voice Input |
| **B** | No / Back | - |

**On-Screen Hints**: Show "[YES] [NO]" at bottom during QUESTION mode

---

## Power Optimization

ePaper advantages:
1. **Persistent display**: Image stays when power off
2. **Selective refresh**: Only update changed regions
3. **Low refresh rate**: 30-60 seconds is fine for dashboards

**Deep Sleep Strategy**:
- After 5 minutes idle → full refresh + deep sleep
- Wake on button press or incoming notification
- Display stays visible during sleep (ePaper magic!)

---

## Information Hierarchy

### Priority 1 (Always Visible)
- Current time
- Battery status
- Agent/system status

### Priority 2 (Dashboard)
- Active tasks
- Notifications
- Network info

### Priority 3 (On-Demand)
- Calendar
- System stats
- Detailed logs

---

## Comparison: M5 vs ePaper

| Feature | M5 TFT (135x240) | ePaper (200x200) |
|---------|------------------|------------------|
| **Display** | Colorful, animated | High contrast, static |
| **Info Density** | 1-2 data points | 6+ data points |
| **Readability** | Indoors | Anywhere (sunlight!) |
| **Power** | Backlight = drain | Refresh-only |
| **Use Case** | Glanceable alerts | Persistent dashboard |
| **Refresh** | 60 FPS animations | 30-60 sec updates |

---

## Next Steps

1. **Hardware Validation**: Identify exact ePaper controller (SSD1680? IL3897?)
2. **Pin Mapping**: Verify GPIO assignments from board schematic
3. **Test Compile**: Validate ESPHome config
4. **Dashboard Iteration**: Refine layouts based on real use
5. **Bridge Integration**: Ensure bridge.py works with new device

---

## Open Questions

- [ ] Exact ePaper driver IC?
- [ ] How to read battery from ETA6098 PMIC?
- [ ] RTC (PCF85063) - does ESPHome support it?
- [ ] Audio codec (ES8311) - needed for voice input?
- [ ] MicroSD slot - use for logs/caching?

---

**Design Goal**: Make the ePaper pager the **most information-dense, readable notification device** in your ecosystem. Think: wrist-mounted system dashboard.
