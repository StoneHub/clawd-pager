# ProGuard rules for Clawdbot Pager

# Keep OkHttp
-dontwarn okhttp3.**
-dontwarn okio.**
-keep class okhttp3.** { *; }
-keep class okio.** { *; }

# Keep Kotlin serialization
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.AnnotationsKt
-keepclassmembers class kotlinx.serialization.json.** {
    *** Companion;
}
-keepclasseswithmembers class kotlinx.serialization.json.** {
    kotlinx.serialization.KSerializer serializer(...);
}
-keep,includedescriptorclasses class com.stonehub.clawdpager.**$$serializer { *; }
-keepclassmembers class com.stonehub.clawdpager.** {
    *** Companion;
}
-keepclasseswithmembers class com.stonehub.clawdpager.** {
    kotlinx.serialization.KSerializer serializer(...);
}

# Keep data classes
-keep class com.stonehub.clawdpager.data.** { *; }
