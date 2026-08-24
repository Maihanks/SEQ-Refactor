package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass8Test {

    @Test
    void m0_messagechainsBehaves() {
        GodClass8 subject = new GodClass8();
        assertEquals("bbcxxxxxxx", subject.m0_messagechains(" ABCDEF "));
    }

}
