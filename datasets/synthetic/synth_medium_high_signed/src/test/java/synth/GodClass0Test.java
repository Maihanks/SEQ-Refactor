package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass0Test {

    @Test
    void m0_messagechainsBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals("bbcxxxxxxx", subject.m0_messagechains(" ABCDEF "));
    }

    @Test
    void m1_longmethodBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals(944, subject.m1_longmethod(50));
    }

}
