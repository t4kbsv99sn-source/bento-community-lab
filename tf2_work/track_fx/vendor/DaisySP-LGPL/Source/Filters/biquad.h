/*
Copyright (c) 2023 Electrosmith, Corp, Hans Mikelson, Matt Gerassimoff, John ffitch, Steven Yi

Use of this source code is governed by the LGPL V2.1
license that can be found in the LICENSE file or at
https://opensource.org/license/lgpl-2-1/
*/

#pragma once
#ifndef DSY_BIQUAD_H
#define DSY_BIQUAD_H

#include <stdint.h>
#ifdef __cplusplus

namespace daisysp
{
/** Two pole recursive filter */
class Biquad
{
  public:
    Biquad() {}
    ~Biquad() {}
    /** Initializes the biquad module.
        \param sample_rate - The sample rate of the audio engine being run. 
    */
    void Init(float sample_rate);


    /** Filters the input signal
        \return filtered output
    */
    float Process(float in);


    /** Sets resonance amount
        \param res : Set filter resonance.
    */
    inline void SetRes(float res)
    {
        res_ = res;
        Reset();
    }


    /** Sets filter cutoff in Hz
        \param cutoff : Set filter cutoff.
    */
    inline void SetCutoff(float cutoff)
    {
        cutoff_ = cutoff;
        Reset();
    }

    // BENTO T1: normalized cookbook coefficients; retain recursive state.
    void SetCoefficients(float b0,float b1,float b2,float a1,float a2)
    { b0_=b0; b1_=b1; b2_=b2; a0_=1.0f; a1_=a1; a2_=a2; }

  private:
    float sample_rate_, cutoff_, res_, b0_, b1_, b2_, a0_, a1_, a2_,
        two_pi_d_sr_, xnm1_, xnm2_, ynm1_, ynm2_;
    void Reset();
};
} // namespace daisysp
#endif
#endif
