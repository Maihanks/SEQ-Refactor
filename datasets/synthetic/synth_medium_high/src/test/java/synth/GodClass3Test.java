package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass3Test {

    @Test
    void m0_longmethodBehaves() {
        GodClass3 subject = new GodClass3();
        assertEquals(113, subject.m0_longmethod(3));
    }

}
