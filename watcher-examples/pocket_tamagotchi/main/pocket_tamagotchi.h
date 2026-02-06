#pragma once

#include <stdint.h>
#include <stdbool.h>

// --- Pet State ---

typedef enum {
    MOOD_HAPPY,
    MOOD_CONTENT,
    MOOD_HUNGRY,
    MOOD_SAD,
    MOOD_SLEEPING,
} pet_mood_t;

typedef struct {
    uint8_t hunger;         // 0 = full, 100 = starving
    uint8_t happiness;      // 0 = miserable, 100 = ecstatic
    uint8_t energy;         // 0 = exhausted, 100 = wired
    uint8_t age_days;       // Days alive
    uint32_t born_epoch;    // Seconds since boot when created
    uint32_t last_fed;      // Seconds since boot
    uint32_t last_petted;   // Seconds since boot
    uint32_t last_seen;     // Last time camera detected someone
    bool is_sleeping;
    pet_mood_t mood;
} pet_state_t;

// --- Constants ---

#define PET_NAME            "Lobster"
#define HUNGER_RATE         2       // Hunger points per minute
#define HAPPINESS_DECAY     1       // Happiness points per minute
#define ENERGY_REGEN        3       // Energy points per minute while sleeping
#define ENERGY_DRAIN        1       // Energy points per minute while awake
#define FEED_AMOUNT         30      // Hunger reduction per feed
#define PET_HAPPINESS_BOOST 20      // Happiness boost per pet
#define PRESENCE_BOOST      5       // Happiness boost when owner detected
#define SLEEP_THRESHOLD     15      // Energy level to auto-sleep
#define WAKE_THRESHOLD      80      // Energy level to auto-wake

#define NVS_NAMESPACE       "tamagotchi"
#define NVS_KEY_HUNGER      "hunger"
#define NVS_KEY_HAPPINESS   "happiness"
#define NVS_KEY_ENERGY      "energy"
#define NVS_KEY_AGE         "age_days"

// --- Display ---

#define SCREEN_SIZE         412
#define PET_BODY_RADIUS     60
#define EYE_RADIUS          10
#define PUPIL_RADIUS        5

// Colors (LVGL format)
#define COLOR_BG            lv_color_hex(0x1a1a2e)
#define COLOR_PET_BODY      lv_color_hex(0xFF6B6B)
#define COLOR_PET_CHEEK     lv_color_hex(0xFFADAD)
#define COLOR_EYE_WHITE     lv_color_hex(0xFFFFFF)
#define COLOR_PUPIL         lv_color_hex(0x2d2d2d)
#define COLOR_HAPPY         lv_color_hex(0x4ade80)
#define COLOR_HUNGRY        lv_color_hex(0xfbbf24)
#define COLOR_SAD           lv_color_hex(0xf87171)
#define COLOR_SLEEPING      lv_color_hex(0x818cf8)
#define COLOR_BAR_BG        lv_color_hex(0x333355)
#define COLOR_TEXT           lv_color_hex(0xe0e0ff)
#define COLOR_TEXT_DIM       lv_color_hex(0x808099)
