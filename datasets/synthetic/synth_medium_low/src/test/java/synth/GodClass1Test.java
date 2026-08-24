package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass1Test {

    @Test
    void m0_messagechainsBehaves() {
        GodClass1 subject = new GodClass1();
        assertEquals("bbcxxxxxxxx", subject.m0_messagechains(" ABCDEF "));
    }

    @Test
    void m1_messagechainsBehaves() {
        GodClass1 subject = new GodClass1();
        assertEquals("bbcxxxxx", subject.m1_messagechains(" ABCDEF "));
    }

}
