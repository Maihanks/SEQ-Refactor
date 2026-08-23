package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass4Test {

    @Test
    void m0_longmethodBehaves() {
        GodClass4 subject = new GodClass4();
        assertEquals(113, subject.m0_longmethod(3));
    }

    @Test
    void m1_longmethodBehaves() {
        GodClass4 subject = new GodClass4();
        assertEquals(113, subject.m1_longmethod(3));
    }

}
