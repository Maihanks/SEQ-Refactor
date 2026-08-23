package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass2Test {

    @Test
    void m0_bigswitchBehaves() {
        GodClass2 subject = new GodClass2();
        assertEquals("two", subject.m0_bigswitch(2));
    }

    @Test
    void m1_messagechainsBehaves() {
        GodClass2 subject = new GodClass2();
        assertEquals("bbc", subject.m1_messagechains(" ABCDEF "));
    }

}
