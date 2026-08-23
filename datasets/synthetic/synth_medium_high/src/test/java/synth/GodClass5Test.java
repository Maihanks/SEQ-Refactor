package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass5Test {

    @Test
    void m0_longmethodBehaves() {
        GodClass5 subject = new GodClass5();
        assertEquals(113, subject.m0_longmethod(3));
    }

}
