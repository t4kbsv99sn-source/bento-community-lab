/*
Copyright (c) 2020 Electrosmith, Corp, Emilie Gillet

Use of this source code is governed by an MIT-style
license that can be found in the LICENSE file or at
https://opensource.org/licenses/MIT.
*/

#pragma once
#ifndef DSY_SYNTHBD_H
#define DSY_SYNTHBD_H

#include "Filters/svf.h"
#include "Utility/dsp.h"

#include <stdint.h>
#ifdef __cplusplus

/** @file synthbassdrum.h */

namespace daisysp
{
/**  
       @brief Click noise for SyntheticBassDrum
       @author Ben Sergentanis
       @date Jan 2021
       Ported from pichenettes/eurorack/plaits/dsp/drums/synthetic_bass_drum.h \n
       to an independent module. \n
       Original code written by Emilie Gillet in 2016. \n
*/
class SyntheticBassDrumClick
{
  public:
    SyntheticBassDrumClick() {}
    ~SyntheticBassDrumClick() {}

    /** Init the module
        \param sample_rate Audio engine sample rate.
    */
    void Init(float sample_rate);

    /** Get the next sample.
        \param in Trigger the click.
    */
    float Process(float in);

  private:
    float lp_;
    float hp_;
    Svf   filter_;
};

/**  
       @brief Attack Noise generator for SyntheticBassDrum. 
       @author Ben Sergentanis
       @date Jan 2021
       Ported from pichenettes/eurorack/plaits/dsp/drums/synthetic_bass_drum.h \n
       to an independent module. \n
       Original code written by Emilie Gillet in 2016. \n
*/
class SyntheticBassDrumAttackNoise
{
  public:
    SyntheticBassDrumAttackNoise() {}
    ~SyntheticBassDrumAttackNoise() {}

    /** Init the module */
    void Init();

    /** Get the next sample. */
    float Process();

  private:
    float lp_;
    float hp_;
};

/**  
       @brief Naive bass drum model (modulated oscillator with FM + envelope).
       @author Ben Sergentanis
       @date Jan 2021
       Inadvertently 909-ish. \n \n 
       Ported from pichenettes/eurorack/plaits/dsp/drums/synthetic_bass_drum.h \n
       to an independent module. \n
       Original code written by Emilie Gillet in 2016. \n
*/
class SyntheticBassDrum
{
  public:
    SyntheticBassDrum() {}
    ~SyntheticBassDrum() {}

    /** Init the module
        \param sample_rate Audio engine sample rate.
    */
    void Init(float sample_rate);

    /** Generates a distorted sine wave */
    inline float DistortedSine(float phase, float phase_noise, float dirtiness);

    /** Transistor VCA simulation.
        \param s Input sample.
        \param gain VCA gain.
    */
    inline float TransistorVCA(float s, float gain);

    /** Get the next sample.
        \param trigger True triggers the BD. This is optional.
    */
    float Process(bool trigger = false);

    /** Trigger the drum */
    void Trig();

    /* Bento: call after parameter changes; cache sample-invariant coefficients. */
    void UpdateCoefficients();

    /** Allows the drum to play continuously
        \param sustain True sets the drum on infinite sustain.
    */
    void SetSustain(bool sustain);

    /** Sets the amount of accent.
        \param accent Works 0-1.
    */
    void SetAccent(float accent);

    /** Set the bass drum's root frequency.
        \param Frequency in Hz.
    */
    void SetFreq(float freq);

    /** Sets the overall bright / darkness of the drum.
        \param tone Works 0-1.
    */
    void SetTone(float tone);

    // BENTO_MOD K15: independent transient amount; negative default is legacy Tone.
    void SetClick(float click) { click_level_ = fclamp(click, 0.f, 1.f); }

    // BENTO_MOD P10: unclamped sweep depth for the Kick's Punch pitch dive (no new state).
    void SetFmEnvelopeAmountRaw(float amount) { fm_envelope_amount_ = amount; }

    /** Sets how long the drum's volume takes to decay.
        \param Works 0-1.
    */
    void SetDecay(float decay);

    /** Makes things grimy
        \param dirtiness Works 0-1.
    */
    void SetDirtiness(float dirtiness);

    /** Sets how much of a pitch sweep the drum experiences when triggered.
        \param fm_envelope_amount Works 0-1.
    */
    void SetFmEnvelopeAmount(float fm_envelope_amount);

    /** Sets how long the initial pitch sweep takes.
        \param fm_envelope_decay Works 0-1.
    */
    void SetFmEnvelopeDecay(float fm_envelope_decay);

  private:
    float sample_rate_;
    float cached_dirt_,cached_fm_decay_,cached_body_decay_,cached_transient_decay_,cached_tone_f_;

    bool  trig_;
    bool  sustain_;
    float accent_, new_f0_, tone_, decay_;
    float click_level_;
    float dirtiness_, fm_envelope_amount_, fm_envelope_decay_;

    float f0_;
    float phase_;
    float phase_noise_;

    float fm_;
    float fm_lp_;
    float body_env_;
    float body_env_lp_;
    float transient_env_;
    float transient_env_lp_;

    float sustain_gain_;

    float tone_lp_;

    SyntheticBassDrumClick       click_;
    SyntheticBassDrumAttackNoise noise_;

    int body_env_pulse_width_;
    int fm_pulse_width_;
};

} // namespace daisysp
#endif
#endif