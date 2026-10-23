#pragma once
/* CH2: custom actions in the native persistent header (see docs/DISPLAY.md). */
int header_action(void *out,unsigned id,const char *label);
int header_action_lit(void *out,unsigned id,const char *label,int lit);
void header_sync(const void *out);
int header_tab(void *out,unsigned id,const char *label,int active);
