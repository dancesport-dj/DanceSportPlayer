// A C door into Signalsmith Stretch, the pitch-kept time stretch Qt's FFmpeg
// backend uses itself (qtmultimedia 6.12 src/3rdparty/signalsmith-stretch 1.1.0,
// vendored unchanged in signalsmith/). player.audio.stretch_signalsmith loads
// it with ctypes. All buffers are interleaved float32, frames x channels.
//
// Build: build_sstretch.bat (MinGW g++, static, no runtime DLLs needed).
#include "signalsmith/signalsmith-stretch.h"

#if defined(_WIN32)
#define SS_EXPORT extern "C" __declspec(dllexport)
#else
#define SS_EXPORT extern "C" __attribute__((visibility("default")))
#endif

namespace {

using Stretch = signalsmith::stretch::SignalsmithStretch<float>;

// buffer[channel][index] over an interleaved block, as the stretch reads it.
template <class T>
struct Interleaved {
    T *data;
    int channels;
    struct Channel {
        T *data;
        int channels;
        T &operator[](int i) const { return data[i * channels]; }
    };
    Channel operator[](int c) const { return Channel{data + c, channels}; }
};

struct Handle {
    Stretch stretch;
    int channels;
};

}  // namespace

SS_EXPORT void *ss_create(int channels, float sample_rate) {
    Handle *h = new Handle();
    h->channels = channels;
    h->stretch.presetDefault(channels, sample_rate);
    return h;
}

SS_EXPORT void ss_destroy(void *handle) { delete static_cast<Handle *>(handle); }

SS_EXPORT void ss_reset(void *handle) { static_cast<Handle *>(handle)->stretch.reset(); }

SS_EXPORT int ss_input_latency(void *handle) {
    return static_cast<Handle *>(handle)->stretch.inputLatency();
}

SS_EXPORT int ss_output_latency(void *handle) {
    return static_cast<Handle *>(handle)->stretch.outputLatency();
}

SS_EXPORT void ss_seek(void *handle, const float *in, int frames, double rate) {
    Handle *h = static_cast<Handle *>(handle);
    h->stretch.seek(Interleaved<const float>{in, h->channels}, frames, rate);
}

SS_EXPORT void ss_process(void *handle, const float *in, int in_frames, float *out,
                          int out_frames) {
    Handle *h = static_cast<Handle *>(handle);
    h->stretch.process(Interleaved<const float>{in, h->channels}, in_frames,
                       Interleaved<float>{out, h->channels}, out_frames);
}

SS_EXPORT void ss_flush(void *handle, float *out, int frames) {
    Handle *h = static_cast<Handle *>(handle);
    h->stretch.flush(Interleaved<float>{out, h->channels}, frames);
}
