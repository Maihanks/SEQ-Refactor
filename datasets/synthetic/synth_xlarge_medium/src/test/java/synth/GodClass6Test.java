package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass6Test {

    @Test
    void m0_messagechainsBehaves() {
        GodClass6 subject = new GodClass6();
        assertEquals("bbcxxxxxx", subject.m0_messagechains(" ABCDEF "));
    }

}
