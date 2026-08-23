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
    void m1_bigswitchBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals("two", subject.m1_bigswitch(2));
    }

    @Test
    void m2_longmethodBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals(113, subject.m2_longmethod(3));
    }

}
