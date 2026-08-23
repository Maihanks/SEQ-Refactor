package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass1Test {

    @Test
    void m0_longmethodBehaves() {
        GodClass1 subject = new GodClass1();
        assertEquals(113, subject.m0_longmethod(3));
    }

    @Test
    void m1_bigswitchBehaves() {
        GodClass1 subject = new GodClass1();
        assertEquals("two", subject.m1_bigswitch(2));
    }

}
