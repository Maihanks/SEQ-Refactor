package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass0Test {

    @Test
    void m0_bigswitchBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals("two", subject.m0_bigswitch(2));
    }

    @Test
    void m1_messagechainsBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals("bbc", subject.m1_messagechains(" ABCDEF "));
    }

}
