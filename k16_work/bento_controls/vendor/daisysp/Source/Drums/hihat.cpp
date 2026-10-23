#include "dsp.h"
#include "hihat.h"
#include <math.h>

using namespace daisysp;

void SquareNoise::Init(float sample_rate)
{
    for(int i = 0; i < 6; i++)
    {
        phase_[i] = 0;
    }
}

float SquareNoise::Process(float f0)
{
    const float ratios[6] = {// Nominal f0: 414 Hz
                             1.0f,
                             1.304f,
                             1.466f,
                             1.787f,
                             1.932f,
                             2.536f};

    uint32_t increment[6];
    uint32_t phase[6];
    for(int i = 0; i < 6; ++i)
    {
        float f = f0 * ratios[i];
        if(f >= 0.499f)
            f = 0.499f;
        increment[i] = static_cast<uint32_t>(f * 4294967296.0f);
        phase[i]     = phase_[i];
    }

    phase[0] += increment[0];
    phase[1] += increment[1];
    phase[2] += increment[2];
    phase[3] += increment[3];
    phase[4] += increment[4];
    phase[5] += increment[5];
    uint32_t noise = 0;
    noise += (phase[0] >> 31);
    noise += (phase[1] >> 31);
    noise += (phase[2] >> 31);
    noise += (phase[3] >> 31);
    noise += (phase[4] >> 31);
    noise += (phase[5] >> 31);

    for(int i = 0; i < 6; ++i)
    {
        phase_[i] = phase[i];
    }

    return 0.33f * static_cast<float>(noise) - 1.0f;
}

// BENTO_MOD: RingModNoise implementation is not linked in this 808-only build.
