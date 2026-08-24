package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass1Test {

    @Test
    void m0_messagechainsBehaves() {
        GodClass1 subject = new GodClass1();
        assertEquals("bbcxxxxxxxxx", subject.m0_messagechains(" ABCDEF "));
    }

    @Test
    void m1_longmethodBehaves() {
        GodClass1 subject = new GodClass1();
        assertEquals(837, subject.m1_longmethod(50));
    }

}
