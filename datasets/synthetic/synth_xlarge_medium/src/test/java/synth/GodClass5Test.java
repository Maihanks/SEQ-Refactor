package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass5Test {

    @Test
    void m0_longmethodBehaves() {
        GodClass5 subject = new GodClass5();
        assertEquals(944, subject.m0_longmethod(50));
    }

    @Test
    void m1_messagechainsBehaves() {
        GodClass5 subject = new GodClass5();
        assertEquals("bbcxxxxxxxx", subject.m1_messagechains(" ABCDEF "));
    }

}
