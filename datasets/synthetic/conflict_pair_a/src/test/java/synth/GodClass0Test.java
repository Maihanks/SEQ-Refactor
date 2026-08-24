package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass0Test {

    @Test
    void m0_messagechainsBehaves() {
        GodClass0 subject = new GodClass0();
        assertEquals("bbcxxxxxx", subject.m0_messagechains(" ABCDEF "));
    }

}
