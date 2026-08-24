package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass2Test {

    @Test
    void m0_messagechainsBehaves() {
        GodClass2 subject = new GodClass2();
        assertEquals("bbcxxxxxxxx", subject.m0_messagechains(" ABCDEF "));
    }

    @Test
    void m1_longmethodBehaves() {
        GodClass2 subject = new GodClass2();
        assertEquals(944, subject.m1_longmethod(50));
    }

}
