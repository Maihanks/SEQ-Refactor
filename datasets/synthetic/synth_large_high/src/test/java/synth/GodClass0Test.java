package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass0Test {

    @Test
    void m0_longmethodBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals(837, subject.m0_longmethod(50));
    }

    @Test
    void m1_bigswitchBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals("v2", subject.m1_bigswitch(2));
    }

}
