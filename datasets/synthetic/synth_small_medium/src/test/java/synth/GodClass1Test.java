package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass1Test {

    @Test
    void m0_messagechainsBehaves() {
        GodClass1 subject = new GodClass1();
        assertEquals("bbc", subject.m0_messagechains(" ABCDEF "));
    }

}
