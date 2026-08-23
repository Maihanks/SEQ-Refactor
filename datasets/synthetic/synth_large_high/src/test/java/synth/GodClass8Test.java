package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass8Test {

    @Test
    void m0_bigswitchBehaves() {
        GodClass8 subject = new GodClass8();
        assertEquals("two", subject.m0_bigswitch(2));
    }

}
