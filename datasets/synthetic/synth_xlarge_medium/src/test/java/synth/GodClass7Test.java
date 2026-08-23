package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass7Test {

    @Test
    void m0_bigswitchBehaves() {
        GodClass7 subject = new GodClass7();
        assertEquals("two", subject.m0_bigswitch(2));
    }

}
