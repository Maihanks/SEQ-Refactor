package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LeafClass7Test {

    @Test
    void leafSwitchBehaves() {
        LeafClass7 subject = new LeafClass7();
        assertEquals("two", subject.leafSwitch(2));
    }

}
