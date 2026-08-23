package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass2Test {

    @Test
    void m0_messagechainsBehaves() {
        GodClass2 subject = new GodClass2();
        assertEquals("bbc", subject.m0_messagechains(" ABCDEF "));
    }

    @Test
    void m1_bigswitchBehaves() {
        GodClass2 subject = new GodClass2();
        assertEquals("two", subject.m1_bigswitch(2));
    }

}
