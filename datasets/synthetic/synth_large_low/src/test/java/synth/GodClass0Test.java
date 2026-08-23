package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass0Test {

    @Test
    void m0_messagechainsBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals("bbc", subject.m0_messagechains(" ABCDEF "));
    }

    @Test
    void m1_messagechainsBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals("bbc", subject.m1_messagechains(" ABCDEF "));
    }

}
