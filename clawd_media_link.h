#include "esphome.h"

class ClawdMediaLink : public Component, public CustomAPIDevice {
 public:
  uint8_t image_buffer[240 * 135 / 8]; // 1-bit buffer for now to keep it lean

  void setup() override {
    register_service(&ClawdMediaLink::on_push_image, "push_image", {"data"});
  }

  void on_push_image(std::vector<uint8_t> data) {
    ESP_LOGD("ClawdMedia", "Received image data: %d bytes", data.size());
    // Logic to copy data to buffer will go here
  }
};
