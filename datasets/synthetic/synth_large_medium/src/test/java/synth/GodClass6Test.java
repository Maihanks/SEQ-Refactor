package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass6Test {

    @Test
    void m0_longmethodBehaves() {
        GodClass6 subject = new GodClass6();
        assertEquals(113, subject.m0_longmethod(3));
    }

}
