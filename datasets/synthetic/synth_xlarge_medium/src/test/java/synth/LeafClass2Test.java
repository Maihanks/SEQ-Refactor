package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LeafClass2Test {

    @Test
    void leafSwitchBehaves() {
        LeafClass2 subject = new LeafClass2();
        assertEquals("v2", subject.leafSwitch(2));
    }

}
