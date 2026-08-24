package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass2Test {

    @Test
    void m0_messagechainsBehaves() {
        GodClass2 subject = new GodClass2();
        assertEquals("bbcxxxxxx", subject.m0_messagechains(" ABCDEF "));
    }

}
