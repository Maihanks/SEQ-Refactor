package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass2Test {

    @Test
    void m0_longmethodBehaves() {
        GodClass2 subject = new GodClass2();
        assertEquals(944, subject.m0_longmethod(50));
    }

    @Test
    void m1_messagechainsBehaves() {
        GodClass2 subject = new GodClass2();
        assertEquals("bbcxxxxxxx", subject.m1_messagechains(" ABCDEF "));
    }

}
