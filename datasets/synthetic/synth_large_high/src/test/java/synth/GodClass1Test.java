package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass1Test {

    @Test
    void m0_bigswitchBehaves() {
        GodClass1 subject = new GodClass1();
        assertEquals("v2", subject.m0_bigswitch(2));
    }

    @Test
    void m1_longmethodBehaves() {
        GodClass1 subject = new GodClass1();
        assertEquals(944, subject.m1_longmethod(50));
    }

}
