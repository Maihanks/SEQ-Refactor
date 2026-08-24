package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass2Test {

    @Test
    void m0_longmethodBehaves() {
        GodClass2 subject = new GodClass2();
        assertEquals(837, subject.m0_longmethod(50));
    }

}
