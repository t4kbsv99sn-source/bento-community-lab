/*
Copyright (c) 2020 Electrosmith, Corp

Use of this source code is governed by an MIT-style
license that can be found in the LICENSE file or at
https://opensource.org/licenses/MIT.
*/

#pragma once
#ifndef DSY_SVF_H
#define DSY_SVF_H
#include <math.h>

namespace daisysp
{
/**      Double Sampled, Stable State Variable Filter

Credit to Andrew Simper from musicdsp.org

This is his "State Variable Filter (Double Sampled, Stable)"

Additional thanks to Laurent de Soras for stability limit, and 
Stefan Diedrichsen for the correct notch output

Ported by: Stephen Hensley
*/
class Svf
{
  public:
    Svf() {}
    ~Svf() {}
    /** Initializes the filter
        float sample_rate - sample rate of the audio engine being run, and the frequency that the Process function will be called.
    */
    void Init(float sample_rate);


    /** 
        Process the input signal, updating all of the outputs.
    */
    void Process(float in);


    /** sets the frequency of the cutoff frequency. 
        f must be between 0.0 and sample_rate / 3
    */
    void SetFreq(float f);

    /* Bento S1: identical SetFreq math, with the resonance-dependent term
       prepared once per block. Does not change the existing drum API. */
    inline void SetFreqPrepared(float f, float resonance_damping)
    {
        fc_ = f < 1.0e-6f ? 1.0e-6f : f > fc_max_ ? fc_max_ : f;
        float norm = fc_ / (sr_ * 2.0f);
        freq_ = 2.0f * sinf(3.14159265358979323846f * (norm < .25f ? norm : .25f));
        float limit = 2.0f / freq_ - freq_ * .5f;
        if(limit > 2.0f)limit = 2.0f;
        damp_ = resonance_damping < limit ? resonance_damping : limit;
    }

    /** sets the resonance of the filter.
        Must be between 0.0 and 1.0 to ensure stability.
    */
    void SetRes(float r);

    /** sets the drive of the filter 
        affects the response of the resonance of the filter
    */
    void SetDrive(float d);
    /** lowpass output
        \return low pass output of the filter
    */
    /* Bento port (CH12): Process() returning one output. Same two passes and
       the same statements, so the returned value and the state that carries
       over (low_, band_) are bit-identical to Process() and then Low(),
       High() or Band(). The other outputs are not updated. */
    inline float ProcessLow(float in)
    {
        float band = band_, low = low_;
        float notch = in - damp_ * band;
        low         = low + freq_ * band;
        float high  = notch - low;
        band        = freq_ * high + band - drive_ * band * band * band;
        float out   = 0.5f * low;
        notch       = in - damp_ * band;
        low         = low + freq_ * band;
        high        = notch - low;
        band        = freq_ * high + band - drive_ * band * band * band;
        out += 0.5f * low;
        band_ = band;
        low_  = low;
        return out;
    }
    inline float ProcessHigh(float in)
    {
        float band = band_, low = low_;
        float notch = in - damp_ * band;
        low         = low + freq_ * band;
        float high  = notch - low;
        band        = freq_ * high + band - drive_ * band * band * band;
        float out   = 0.5f * high;
        notch       = in - damp_ * band;
        low         = low + freq_ * band;
        high        = notch - low;
        band        = freq_ * high + band - drive_ * band * band * band;
        out += 0.5f * high;
        band_ = band;
        low_  = low;
        return out;
    }
    inline float ProcessBand(float in)
    {
        float band = band_, low = low_;
        float notch = in - damp_ * band;
        low         = low + freq_ * band;
        float high  = notch - low;
        band        = freq_ * high + band - drive_ * band * band * band;
        float out   = 0.5f * band;
        notch       = in - damp_ * band;
        low         = low + freq_ * band;
        high        = notch - low;
        band        = freq_ * high + band - drive_ * band * band * band;
        out += 0.5f * band;
        band_ = band;
        low_  = low;
        return out;
    }

    inline float Low() { return out_low_; }
    /** highpass output
        \return high pass output of the filter
    */
    inline float High() { return out_high_; }
    /** bandpass output
        \return band pass output of the filter
    */
    inline float Band() { return out_band_; }
    /** notchpass output
        \return notch pass output of the filter
    */
    inline float Notch() { return out_notch_; }
    /** peak output
        \return peak output of the filter
    */
    inline float Peak() { return out_peak_; }

  private:
    float sr_, fc_, res_, drive_, freq_, damp_;
    float notch_, low_, high_, band_, peak_;
    float input_;
    float out_low_, out_high_, out_band_, out_peak_, out_notch_;
    float pre_drive_, fc_max_;
};
} // namespace daisysp

#endif
