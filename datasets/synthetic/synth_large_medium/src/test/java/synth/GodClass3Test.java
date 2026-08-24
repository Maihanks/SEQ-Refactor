package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass3Test {

    @Test
    void m0_messagechainsBehaves() {
        GodClass3 subject = new GodClass3();
        assertEquals("bbcxxxxxx", subject.m0_messagechains(" ABCDEF "));
    }

    @Test
    void m1_bigswitchBehaves() {
        GodClass3 subject = new GodClass3();
        assertEquals("v2", subject.m1_bigswitch(2));
    }

}
