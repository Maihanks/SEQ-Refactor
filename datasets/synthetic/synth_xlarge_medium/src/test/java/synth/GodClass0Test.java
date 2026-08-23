package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass0Test {

    @Test
    void m0_longmethodBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals(113, subject.m0_longmethod(3));
    }

    @Test
    void m1_messagechainsBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals("bbc", subject.m1_messagechains(" ABCDEF "));
    }

}
