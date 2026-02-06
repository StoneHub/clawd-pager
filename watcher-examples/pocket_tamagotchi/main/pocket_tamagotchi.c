/**
 * Pocket Tamagotchi - AI-aware virtual pet for SenseCAP Watcher W1-A
 *
 * A virtual pet that lives on the Watcher's round 412x412 display.
 * The AI camera detects when you're nearby (presence = attention).
 * Knob rotation feeds the pet. Knob button press pets it.
 * RGB LED reflects mood. State persists across power cycles via NVS.
 *
 * Controls:
 *   Knob rotate    → Feed (reduces hunger)
 *   Knob press     → Pet (boosts happiness)
 *   Knob long-press → Toggle sleep / power off
 *   Camera detect   → Presence boost (pet knows you're there)
 */

#include <stdio.h>
#include <string.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "sensecap-watcher.h"
#include "iot_knob.h"
#include "pocket_tamagotchi.h"

static const char *TAG = "tamagotchi";

// --- Global State ---

static pet_state_t pet;
static lv_disp_t *disp = NULL;
static sscma_client_handle_t ai_client = NULL;
static knob_handle_t knob_handle = NULL;
static bool owner_present = false;

// LVGL objects
static lv_obj_t *scr = NULL;
static lv_obj_t *lbl_name = NULL;
static lv_obj_t *lbl_mood = NULL;
static lv_obj_t *lbl_status = NULL;
static lv_obj_t *bar_hunger = NULL;
static lv_obj_t *bar_happiness = NULL;
static lv_obj_t *bar_energy = NULL;
static lv_obj_t *canvas_pet = NULL;
static lv_color_t *canvas_buf = NULL;

// --- NVS Persistence ---

static void save_state(void)
{
    nvs_handle_t h;
    if (nvs_open(NVS_NAMESPACE, NVS_READWRITE, &h) == ESP_OK) {
        nvs_set_u8(h, NVS_KEY_HUNGER, pet.hunger);
        nvs_set_u8(h, NVS_KEY_HAPPINESS, pet.happiness);
        nvs_set_u8(h, NVS_KEY_ENERGY, pet.energy);
        nvs_set_u8(h, NVS_KEY_AGE, pet.age_days);
        nvs_commit(h);
        nvs_close(h);
    }
}

static void load_state(void)
{
    nvs_handle_t h;
    if (nvs_open(NVS_NAMESPACE, NVS_READWRITE, &h) == ESP_OK) {
        nvs_get_u8(h, NVS_KEY_HUNGER, &pet.hunger);
        nvs_get_u8(h, NVS_KEY_HAPPINESS, &pet.happiness);
        nvs_get_u8(h, NVS_KEY_ENERGY, &pet.energy);
        nvs_get_u8(h, NVS_KEY_AGE, &pet.age_days);
        nvs_close(h);
        ESP_LOGI(TAG, "Loaded: hunger=%d happy=%d energy=%d age=%d",
                 pet.hunger, pet.happiness, pet.energy, pet.age_days);
    } else {
        // First boot — new pet
        pet.hunger = 30;
        pet.happiness = 70;
        pet.energy = 80;
        pet.age_days = 0;
        ESP_LOGI(TAG, "New pet born!");
    }
}

// --- Pet Logic ---

static uint32_t now_sec(void)
{
    return (uint32_t)(esp_timer_get_time() / 1000000ULL);
}

static void clamp(uint8_t *val, uint8_t lo, uint8_t hi)
{
    if (*val < lo) *val = lo;
    if (*val > hi) *val = hi;
}

static void update_mood(void)
{
    if (pet.is_sleeping) {
        pet.mood = MOOD_SLEEPING;
    } else if (pet.hunger > 70) {
        pet.mood = MOOD_HUNGRY;
    } else if (pet.happiness < 30) {
        pet.mood = MOOD_SAD;
    } else if (pet.happiness > 70 && pet.hunger < 40) {
        pet.mood = MOOD_HAPPY;
    } else {
        pet.mood = MOOD_CONTENT;
    }
}

static void pet_tick(void)
{
    // Called once per second
    static uint32_t tick_count = 0;
    tick_count++;

    // Every 30 seconds: decay/regen stats
    if (tick_count % 30 == 0) {
        if (pet.is_sleeping) {
            pet.energy += ENERGY_REGEN;
            // Hunger still increases while sleeping, just slower
            pet.hunger += HUNGER_RATE / 2;
            if (pet.energy >= WAKE_THRESHOLD) {
                pet.is_sleeping = false;
                ESP_LOGI(TAG, "Pet woke up!");
            }
        } else {
            pet.hunger += HUNGER_RATE;
            if (pet.happiness > 0) pet.happiness -= HAPPINESS_DECAY;
            if (pet.energy > 0) pet.energy -= ENERGY_DRAIN;

            // Presence boost
            if (owner_present && pet.happiness <= 95) {
                pet.happiness += PRESENCE_BOOST;
            }

            // Auto-sleep when exhausted
            if (pet.energy <= SLEEP_THRESHOLD) {
                pet.is_sleeping = true;
                ESP_LOGI(TAG, "Pet fell asleep (exhausted)");
            }
        }

        clamp(&pet.hunger, 0, 100);
        clamp(&pet.happiness, 0, 100);
        clamp(&pet.energy, 0, 100);
        update_mood();
    }

    // Every 5 minutes: persist state
    if (tick_count % 300 == 0) {
        save_state();
    }

    // Every 24 hours (86400 ticks): age up
    if (tick_count % 86400 == 0 && tick_count > 0) {
        pet.age_days++;
        ESP_LOGI(TAG, "Pet aged to %d days!", pet.age_days);
    }
}

static void feed_pet(void)
{
    if (pet.is_sleeping) return;
    if (pet.hunger > FEED_AMOUNT) {
        pet.hunger -= FEED_AMOUNT;
    } else {
        pet.hunger = 0;
    }
    pet.last_fed = now_sec();
    update_mood();
    ESP_LOGI(TAG, "Fed! hunger=%d", pet.hunger);
}

static void pet_pet(void)
{
    if (pet.is_sleeping) {
        // Petting wakes a sleeping pet
        pet.is_sleeping = false;
        ESP_LOGI(TAG, "Pet woken by petting!");
    }
    pet.happiness += PET_HAPPINESS_BOOST;
    clamp(&pet.happiness, 0, 100);
    pet.last_petted = now_sec();
    update_mood();
    ESP_LOGI(TAG, "Petted! happiness=%d", pet.happiness);
}

// --- RGB LED Mood ---

static void update_led(void)
{
    switch (pet.mood) {
        case MOOD_HAPPY:    bsp_rgb_set(0, 200, 80);  break;
        case MOOD_CONTENT:  bsp_rgb_set(0, 100, 200);  break;
        case MOOD_HUNGRY:   bsp_rgb_set(200, 180, 0);  break;
        case MOOD_SAD:      bsp_rgb_set(200, 60, 60);  break;
        case MOOD_SLEEPING: bsp_rgb_set(20, 20, 60);   break;
    }
}

// --- AI Camera Callbacks ---

static void on_ai_event(sscma_client_handle_t client,
                         const sscma_client_reply_t *reply,
                         void *user_ctx)
{
    sscma_client_box_t *boxes = NULL;
    int count = 0;
    if (sscma_utils_fetch_boxes_from_reply(reply, &boxes, &count) == ESP_OK) {
        bool was_present = owner_present;
        owner_present = (count > 0);
        if (owner_present && !was_present) {
            pet.last_seen = now_sec();
            ESP_LOGI(TAG, "Owner detected! (%d objects)", count);
        }
        free(boxes);
    }
}

static void on_ai_log(sscma_client_handle_t client,
                       const sscma_client_reply_t *reply,
                       void *user_ctx)
{
    // Suppress noisy AI logs
}

// --- Knob Callbacks ---

static void knob_feed_cb(void *arg, void *data)
{
    feed_pet();
}

static void knob_press_cb(void *arg, void *data)
{
    pet_pet();
}

static void knob_long_press_cb(void)
{
    if (!pet.is_sleeping) {
        pet.is_sleeping = true;
        ESP_LOGI(TAG, "Manual sleep");
    } else {
        save_state();
        ESP_LOGI(TAG, "Shutting down...");
        bsp_rgb_set(0, 0, 0);
        bsp_system_deep_sleep(0);
    }
}

// --- Display ---

static const char *mood_emoji(pet_mood_t m)
{
    switch (m) {
        case MOOD_HAPPY:    return "Happy!";
        case MOOD_CONTENT:  return "Content";
        case MOOD_HUNGRY:   return "Hungry...";
        case MOOD_SAD:      return "Sad";
        case MOOD_SLEEPING: return "Zzz...";
    }
    return "?";
}

static lv_color_t mood_color(pet_mood_t m)
{
    switch (m) {
        case MOOD_HAPPY:    return COLOR_HAPPY;
        case MOOD_CONTENT:  return lv_color_hex(0x60a5fa);
        case MOOD_HUNGRY:   return COLOR_HUNGRY;
        case MOOD_SAD:      return COLOR_SAD;
        case MOOD_SLEEPING: return COLOR_SLEEPING;
    }
    return COLOR_TEXT;
}

static lv_obj_t *create_stat_bar(lv_obj_t *parent, int y, const char *label_text,
                                  lv_color_t color)
{
    // Label
    lv_obj_t *lbl = lv_label_create(parent);
    lv_label_set_text(lbl, label_text);
    lv_obj_set_style_text_font(lbl, &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(lbl, COLOR_TEXT_DIM, 0);
    lv_obj_set_pos(lbl, 80, y);

    // Bar
    lv_obj_t *bar = lv_bar_create(parent);
    lv_obj_set_size(bar, 180, 14);
    lv_obj_set_pos(bar, 160, y + 2);
    lv_bar_set_range(bar, 0, 100);
    lv_obj_set_style_bg_color(bar, COLOR_BAR_BG, LV_PART_MAIN);
    lv_obj_set_style_bg_color(bar, color, LV_PART_INDICATOR);
    lv_obj_set_style_radius(bar, 4, LV_PART_MAIN);
    lv_obj_set_style_radius(bar, 4, LV_PART_INDICATOR);

    return bar;
}

static void draw_pet_face(uint32_t tick)
{
    if (!canvas_pet) return;

    int cx = 100, cy = 90;
    float bounce = sinf(tick * 0.08f) * 4.0f;
    int body_y = cy + (int)bounce;

    lv_draw_rect_dsc_t rect_dsc;
    lv_draw_rect_dsc_init(&rect_dsc);

    // Clear canvas
    rect_dsc.bg_color = COLOR_BG;
    rect_dsc.bg_opa = LV_OPA_COVER;
    rect_dsc.radius = 0;
    lv_canvas_draw_rect(canvas_pet, 0, 0, 200, 200, &rect_dsc);

    // Body
    rect_dsc.bg_color = COLOR_PET_BODY;
    rect_dsc.radius = PET_BODY_RADIUS;
    lv_canvas_draw_rect(canvas_pet, cx - PET_BODY_RADIUS, body_y - PET_BODY_RADIUS,
                        PET_BODY_RADIUS * 2, PET_BODY_RADIUS * 2, &rect_dsc);

    // Cheeks
    rect_dsc.bg_color = COLOR_PET_CHEEK;
    rect_dsc.bg_opa = LV_OPA_70;
    rect_dsc.radius = 12;
    lv_canvas_draw_rect(canvas_pet, cx - 45, body_y + 5, 24, 16, &rect_dsc);
    lv_canvas_draw_rect(canvas_pet, cx + 21, body_y + 5, 24, 16, &rect_dsc);
    rect_dsc.bg_opa = LV_OPA_COVER;

    // Eyes
    if (pet.is_sleeping) {
        // Closed eyes (horizontal lines)
        rect_dsc.bg_color = COLOR_PUPIL;
        rect_dsc.radius = 2;
        lv_canvas_draw_rect(canvas_pet, cx - 28, body_y - 5, 16, 3, &rect_dsc);
        lv_canvas_draw_rect(canvas_pet, cx + 12, body_y - 5, 16, 3, &rect_dsc);
    } else {
        // Eye whites
        rect_dsc.bg_color = COLOR_EYE_WHITE;
        rect_dsc.radius = EYE_RADIUS;
        lv_canvas_draw_rect(canvas_pet, cx - 28, body_y - 14,
                            EYE_RADIUS * 2, EYE_RADIUS * 2, &rect_dsc);
        lv_canvas_draw_rect(canvas_pet, cx + 8, body_y - 14,
                            EYE_RADIUS * 2, EYE_RADIUS * 2, &rect_dsc);

        // Pupils — follow owner presence
        int pupil_offset_x = owner_present ? 2 : 0;
        int pupil_offset_y = owner_present ? 1 : 0;
        rect_dsc.bg_color = COLOR_PUPIL;
        rect_dsc.radius = PUPIL_RADIUS;
        lv_canvas_draw_rect(canvas_pet,
                            cx - 28 + (EYE_RADIUS - PUPIL_RADIUS) + pupil_offset_x,
                            body_y - 14 + (EYE_RADIUS - PUPIL_RADIUS) + pupil_offset_y,
                            PUPIL_RADIUS * 2, PUPIL_RADIUS * 2, &rect_dsc);
        lv_canvas_draw_rect(canvas_pet,
                            cx + 8 + (EYE_RADIUS - PUPIL_RADIUS) + pupil_offset_x,
                            body_y - 14 + (EYE_RADIUS - PUPIL_RADIUS) + pupil_offset_y,
                            PUPIL_RADIUS * 2, PUPIL_RADIUS * 2, &rect_dsc);
    }

    // Mouth — mood-dependent
    rect_dsc.radius = 4;
    if (pet.mood == MOOD_HAPPY) {
        // Smile (wide arc approximated with rounded rect)
        rect_dsc.bg_color = COLOR_PUPIL;
        lv_canvas_draw_rect(canvas_pet, cx - 15, body_y + 15, 30, 8, &rect_dsc);
    } else if (pet.mood == MOOD_SAD || pet.mood == MOOD_HUNGRY) {
        // Frown
        rect_dsc.bg_color = COLOR_PUPIL;
        lv_canvas_draw_rect(canvas_pet, cx - 10, body_y + 20, 20, 4, &rect_dsc);
    } else {
        // Neutral
        rect_dsc.bg_color = COLOR_PUPIL;
        lv_canvas_draw_rect(canvas_pet, cx - 8, body_y + 16, 16, 4, &rect_dsc);
    }
}

static void build_ui(void)
{
    scr = lv_scr_act();
    lv_obj_set_style_bg_color(scr, COLOR_BG, 0);

    // Pet name at top
    lbl_name = lv_label_create(scr);
    lv_label_set_text(lbl_name, PET_NAME);
    lv_obj_set_style_text_font(lbl_name, &lv_font_montserrat_28, 0);
    lv_obj_set_style_text_color(lbl_name, COLOR_TEXT, 0);
    lv_obj_align(lbl_name, LV_ALIGN_TOP_MID, 0, 20);

    // Canvas for pet face (200x200 in center)
    canvas_buf = heap_caps_malloc(LV_CANVAS_BUF_SIZE_TRUE_COLOR(200, 200),
                                   MALLOC_CAP_SPIRAM);
    if (canvas_buf) {
        canvas_pet = lv_canvas_create(scr);
        lv_canvas_set_buffer(canvas_pet, canvas_buf, 200, 200, LV_IMG_CF_TRUE_COLOR);
        lv_obj_align(canvas_pet, LV_ALIGN_TOP_MID, 0, 60);
    }

    // Mood text below pet
    lbl_mood = lv_label_create(scr);
    lv_label_set_text(lbl_mood, "Content");
    lv_obj_set_style_text_font(lbl_mood, &lv_font_montserrat_20, 0);
    lv_obj_set_style_text_color(lbl_mood, COLOR_HAPPY, 0);
    lv_obj_align(lbl_mood, LV_ALIGN_TOP_MID, 0, 270);

    // Stat bars
    bar_hunger    = create_stat_bar(scr, 305, "Hunger", COLOR_HUNGRY);
    bar_happiness = create_stat_bar(scr, 330, "Happy", COLOR_HAPPY);
    bar_energy    = create_stat_bar(scr, 355, "Energy", COLOR_SLEEPING);

    // Status line at bottom
    lbl_status = lv_label_create(scr);
    lv_label_set_text(lbl_status, "Rotate: Feed | Press: Pet");
    lv_obj_set_style_text_font(lbl_status, &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(lbl_status, COLOR_TEXT_DIM, 0);
    lv_obj_align(lbl_status, LV_ALIGN_BOTTOM_MID, 0, -10);
}

static void update_ui(uint32_t tick)
{
    // Mood label
    lv_label_set_text(lbl_mood, mood_emoji(pet.mood));
    lv_obj_set_style_text_color(lbl_mood, mood_color(pet.mood), 0);

    // Stat bars — hunger is inverted (high = bad)
    lv_bar_set_value(bar_hunger, pet.hunger, LV_ANIM_ON);
    lv_bar_set_value(bar_happiness, pet.happiness, LV_ANIM_ON);
    lv_bar_set_value(bar_energy, pet.energy, LV_ANIM_ON);

    // Pet face
    draw_pet_face(tick);

    // Status line
    if (owner_present) {
        lv_label_set_text(lbl_status, "I see you! :)");
    } else if (pet.is_sleeping) {
        lv_label_set_text(lbl_status, "Hold knob to wake or power off");
    } else {
        lv_label_set_text(lbl_status, "Rotate: Feed | Press: Pet");
    }
}

// --- Main ---

void app_main(void)
{
    ESP_LOGI(TAG, "=== Pocket Tamagotchi ===");

    // NVS init
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    // Load saved pet state
    memset(&pet, 0, sizeof(pet));
    load_state();
    pet.born_epoch = now_sec();
    update_mood();

    // BSP init — io expander must be first
    bsp_io_expander_init();

    // RGB LED
    bsp_rgb_init();
    update_led();

    // Display + LVGL
    disp = bsp_lvgl_init();
    if (!disp) {
        ESP_LOGE(TAG, "Display init failed!");
        return;
    }

    // Build UI (under LVGL lock)
    if (lvgl_port_lock(0)) {
        build_ui();
        lvgl_port_unlock();
    }

    // Knob input
    knob_config_t knob_cfg = {
        .default_direction = 0,
        .gpio_encoder_a = BSP_KNOB_A,
        .gpio_encoder_b = BSP_KNOB_B,
    };
    knob_handle = iot_knob_create(&knob_cfg);
    iot_knob_register_cb(knob_handle, KNOB_LEFT, knob_feed_cb, NULL);
    iot_knob_register_cb(knob_handle, KNOB_RIGHT, knob_feed_cb, NULL);

    // Knob button — must be after bsp_lvgl_init (needs encoder setup)
    bsp_set_btn_long_press_cb(knob_long_press_cb);

    // AI camera (optional — graceful if unavailable)
    ai_client = bsp_sscma_client_init();
    if (ai_client) {
        const sscma_client_callback_t ai_cb = {
            .on_event = on_ai_event,
            .on_log = on_ai_log,
        };
        sscma_client_register_callback(ai_client, &ai_cb, NULL);
        sscma_client_init(ai_client);
        sscma_client_set_model(ai_client, 1);
        sscma_client_set_sensor(ai_client, 1, 0, true);
        sscma_client_invoke(ai_client, -1, false, false);
        ESP_LOGI(TAG, "AI camera started");
    } else {
        ESP_LOGW(TAG, "AI camera unavailable — presence detection disabled");
    }

    ESP_LOGI(TAG, "Pet '%s' is alive! Age: %d days", PET_NAME, pet.age_days);

    // Main loop — tick every second, render at ~20 FPS
    uint32_t tick = 0;
    while (1) {
        // Game tick (1 Hz)
        pet_tick();
        update_led();

        // Render at ~20 FPS for 1 second
        for (int frame = 0; frame < 20; frame++) {
            if (lvgl_port_lock(0)) {
                update_ui(tick);
                lvgl_port_unlock();
            }
            tick++;
            vTaskDelay(pdMS_TO_TICKS(50));
        }
    }
}
