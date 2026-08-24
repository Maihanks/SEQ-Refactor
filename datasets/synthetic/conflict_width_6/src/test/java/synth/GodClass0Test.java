package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass0Test {

    @Test
    void m0_bigswitchBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals("v2", subject.m0_bigswitch(2));
    }

    @Test
    void m1_bigswitchBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals("v2", subject.m1_bigswitch(2));
    }

    @Test
    void m2_longmethodBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals(1052, subject.m2_longmethod(50));
    }

    @Test
    void m3_messagechainsBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals("bbcxxxxx", subject.m3_messagechains(" ABCDEF "));
    }

    @Test
    void m4_longmethodBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals(837, subject.m4_longmethod(50));
    }

    @Test
    void m5_messagechainsBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals("bbcxxxxxx", subject.m5_messagechains(" ABCDEF "));
    }

}
