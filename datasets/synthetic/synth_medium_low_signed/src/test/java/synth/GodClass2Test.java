package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass2Test {

    @Test
    void m0_longmethodBehaves() {
        GodClass2 subject = new GodClass2();
        assertEquals(113, subject.m0_longmethod(3));
    }

    @Test
    void m1_messagechainsBehaves() {
        GodClass2 subject = new GodClass2();
        assertEquals("bbc", subject.m1_messagechains(" ABCDEF "));
    }

}
